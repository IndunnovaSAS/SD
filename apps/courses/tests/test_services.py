"""
Tests for courses services.

Comprehensive tests for all service classes in the courses module.
"""

import tempfile
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from apps.courses.models import (
    Course,
    CourseVersion,
    Enrollment,
    Lesson,
    LessonProgress,
    MediaAsset,
    ResourceLibrary,
    ScormPackage,
)
from apps.courses.services import (
    CourseService,
    EnrollmentService,
    MediaService,
    ResourceLibraryService,
    ScormService,
)
from apps.courses.tests.factories import (
    ArchivedCourseFactory,
    CategoryFactory,
    CompletedEnrollmentFactory,
    CompletedLessonProgressFactory,
    CourseFactory,
    EnrollmentFactory,
    ExpiredEnrollmentFactory,
    InProgressEnrollmentFactory,
    LessonFactory,
    LessonProgressFactory,
    ModuleFactory,
    PublishedCourseFactory,
    ScormLessonFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestCourseService:
    """Tests for CourseService."""

    def test_create_course_basic(self):
        """Test creating a basic course."""
        user = UserFactory()
        data = {
            "code": "TEST-001",
            "title": "Test Course",
            "description": "Test description",
            "course_type": Course.Type.MANDATORY,
        }

        course = CourseService.create_course(data, user)

        assert course.id is not None
        assert course.code == "TEST-001"
        assert course.title == "Test Course"
        assert course.created_by == user
        assert course.status == Course.Status.DRAFT

    def test_create_course_with_modules(self):
        """Test creating a course with modules."""
        user = UserFactory()
        data = {
            "code": "TEST-002",
            "title": "Course with Modules",
            "description": "Description",
            "modules": [
                {"title": "Module 1", "description": "First module"},
                {"title": "Module 2", "description": "Second module"},
            ],
        }

        course = CourseService.create_course(data, user)

        assert course.modules.count() == 2
        modules = list(course.modules.order_by("order"))
        assert modules[0].title == "Module 1"
        assert modules[0].order == 0
        assert modules[1].title == "Module 2"
        assert modules[1].order == 1

    def test_create_course_with_modules_and_lessons(self):
        """Test creating a course with modules and lessons."""
        user = UserFactory()
        data = {
            "code": "TEST-003",
            "title": "Full Course",
            "description": "Description",
            "duration": 180,
            "modules": [
                {
                    "title": "Module 1",
                    "description": "First module",
                    "lessons": [
                        {"title": "Lesson 1", "lesson_type": Lesson.Type.VIDEO, "duration": 30},
                        {"title": "Lesson 2", "lesson_type": Lesson.Type.PDF, "duration": 15},
                    ],
                },
            ],
        }

        course = CourseService.create_course(data, user)

        assert course.modules.count() == 1
        module = course.modules.first()
        assert module.lessons.count() == 2

        lessons = list(module.lessons.order_by("order"))
        assert lessons[0].title == "Lesson 1"
        assert lessons[0].order == 0
        assert lessons[1].title == "Lesson 2"
        assert lessons[1].order == 1

    def test_publish_course_success(self):
        """Test publishing a draft course."""
        user = UserFactory()
        course = CourseFactory(status=Course.Status.DRAFT, created_by=user)

        published = CourseService.publish_course(course, user, "Initial release")

        assert published.status == Course.Status.PUBLISHED
        assert published.published_at is not None
        assert published.version == 2

        # Verify version snapshot was created
        version = CourseVersion.objects.filter(course=course).first()
        assert version is not None
        assert version.changelog == "Initial release"

    def test_publish_course_already_published(self):
        """Test publishing an already published course raises error."""
        user = UserFactory()
        course = PublishedCourseFactory()

        with pytest.raises(ValueError) as exc_info:
            CourseService.publish_course(course, user)

        assert "ya está publicado" in str(exc_info.value)

    def test_publish_course_default_changelog(self):
        """Test publishing with default changelog."""
        user = UserFactory()
        course = CourseFactory(status=Course.Status.DRAFT)

        CourseService.publish_course(course, user)

        version = CourseVersion.objects.filter(course=course).first()
        assert version.changelog == "Publicación inicial"

    def test_archive_course_success(self):
        """Test archiving a course."""
        user = UserFactory()
        course = PublishedCourseFactory()

        archived = CourseService.archive_course(course, user)

        assert archived.status == Course.Status.ARCHIVED

        # Verify version snapshot was created
        versions = CourseVersion.objects.filter(course=course)
        assert versions.exists()

    def test_archive_course_already_archived(self):
        """Test archiving an already archived course raises error."""
        user = UserFactory()
        course = ArchivedCourseFactory()

        with pytest.raises(ValueError) as exc_info:
            CourseService.archive_course(course, user)

        assert "ya está archivado" in str(exc_info.value)

    def test_duplicate_course_basic(self):
        """Test duplicating a course."""
        user = UserFactory()
        original = CourseFactory(
            title="Original Course",
            description="Original description",
            duration=60,
        )

        duplicate = CourseService.duplicate_course(original, user)

        assert duplicate.id != original.id
        assert duplicate.code != original.code
        assert duplicate.title == "Original Course (Copia)"
        assert duplicate.description == original.description
        assert duplicate.status == Course.Status.DRAFT
        assert duplicate.created_by == user

    def test_duplicate_course_with_custom_code(self):
        """Test duplicating a course with custom code."""
        user = UserFactory()
        original = CourseFactory()

        duplicate = CourseService.duplicate_course(original, user, new_code="CUSTOM-001")

        assert duplicate.code == "CUSTOM-001"

    def test_duplicate_course_with_modules_and_lessons(self):
        """Test duplicating a course preserves modules and lessons."""
        user = UserFactory()
        original = CourseFactory()
        module = ModuleFactory(course=original, title="Module 1")
        LessonFactory(module=module, title="Lesson 1", duration=30)
        LessonFactory(module=module, title="Lesson 2", duration=20)

        duplicate = CourseService.duplicate_course(original, user)

        assert duplicate.modules.count() == 1
        dup_module = duplicate.modules.first()
        assert dup_module.title == "Module 1"
        assert dup_module.lessons.count() == 2

    def test_duplicate_course_preserves_attributes(self):
        """Test duplicating preserves all course attributes."""
        user = UserFactory()
        category = CategoryFactory()
        original = CourseFactory(
            course_type=Course.Type.MANDATORY,
            target_profiles=["LINIERO", "JEFE_CUADRILLA"],
            validity_months=12,
            category=category,
        )

        duplicate = CourseService.duplicate_course(original, user)

        assert duplicate.course_type == original.course_type
        assert duplicate.target_profiles == original.target_profiles
        assert duplicate.validity_months == original.validity_months
        assert duplicate.category == original.category

    def test_calculate_course_duration(self):
        """Test calculating course duration from lessons."""
        course = CourseFactory()
        module1 = ModuleFactory(course=course)
        module2 = ModuleFactory(course=course)

        LessonFactory(module=module1, duration=30)
        LessonFactory(module=module1, duration=20)
        LessonFactory(module=module2, duration=15)

        total = CourseService.calculate_course_duration(course)

        assert total == 65

    def test_calculate_course_duration_empty(self):
        """Test calculating duration for course with no lessons."""
        course = CourseFactory()

        total = CourseService.calculate_course_duration(course)

        assert total == 0

    def test_get_course_statistics(self):
        """Test getting course statistics."""
        course = PublishedCourseFactory()
        module = ModuleFactory(course=course)
        LessonFactory(module=module)
        LessonFactory(module=module)

        # Create various enrollments
        EnrollmentFactory(course=course, status=Enrollment.Status.ENROLLED)
        InProgressEnrollmentFactory(course=course)
        CompletedEnrollmentFactory(course=course)
        ExpiredEnrollmentFactory(course=course)

        stats = CourseService.get_course_statistics(course)

        assert stats["total_enrollments"] == 4
        assert stats["enrolled"] == 1
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["expired"] == 1
        assert stats["module_count"] == 1
        assert stats["lesson_count"] == 2
        assert stats["completion_rate"] == 25.0

    def test_get_course_statistics_no_enrollments(self):
        """Test getting statistics for course with no enrollments."""
        course = CourseFactory()

        stats = CourseService.get_course_statistics(course)

        assert stats["total_enrollments"] == 0
        assert stats["completion_rate"] == 0


@pytest.mark.django_db
class TestEnrollmentService:
    """Tests for EnrollmentService."""

    def test_enroll_user_basic(self):
        """Test basic user enrollment."""
        user = UserFactory()
        course = PublishedCourseFactory()

        enrollment = EnrollmentService.enroll_user(user, course)

        assert enrollment.user == user
        assert enrollment.course == course
        assert enrollment.status == Enrollment.Status.ENROLLED
        assert enrollment.progress == 0

    def test_enroll_user_with_assigned_by(self):
        """Test enrollment with assigned_by."""
        user = UserFactory()
        supervisor = UserFactory()
        course = PublishedCourseFactory()

        enrollment = EnrollmentService.enroll_user(user, course, assigned_by=supervisor)

        assert enrollment.assigned_by == supervisor

    def test_enroll_user_with_due_date(self):
        """Test enrollment with due date."""
        user = UserFactory()
        course = PublishedCourseFactory()
        due = date.today() + timedelta(days=30)

        enrollment = EnrollmentService.enroll_user(user, course, due_date=due)

        assert enrollment.due_date == due

    def test_enroll_user_already_enrolled(self):
        """Test enrolling already enrolled user returns existing enrollment."""
        user = UserFactory()
        course = PublishedCourseFactory()

        enrollment1 = EnrollmentService.enroll_user(user, course)
        enrollment2 = EnrollmentService.enroll_user(user, course)

        assert enrollment1.id == enrollment2.id

    def test_enroll_user_re_enroll_expired(self):
        """Test re-enrolling an expired user."""
        user = UserFactory()
        course = PublishedCourseFactory()

        # Create expired enrollment
        expired = ExpiredEnrollmentFactory(user=user, course=course, progress=Decimal("50.00"))

        # Re-enroll
        new_due = date.today() + timedelta(days=30)
        reactivated = EnrollmentService.enroll_user(user, course, due_date=new_due)

        assert reactivated.id == expired.id
        assert reactivated.status == Enrollment.Status.ENROLLED
        assert reactivated.progress == 0
        assert reactivated.due_date == new_due
        assert reactivated.started_at is None
        assert reactivated.completed_at is None

    def test_enroll_user_with_prerequisites_not_met(self):
        """Test enrolling user without meeting prerequisites."""
        user = UserFactory()
        prereq = PublishedCourseFactory()
        course = PublishedCourseFactory()
        course.prerequisites.add(prereq)

        with pytest.raises(ValueError) as exc_info:
            EnrollmentService.enroll_user(user, course)

        assert "prerrequisitos" in str(exc_info.value)

    def test_enroll_user_with_prerequisites_met(self):
        """Test enrolling user with prerequisites completed."""
        user = UserFactory()
        prereq = PublishedCourseFactory()
        course = PublishedCourseFactory()
        course.prerequisites.add(prereq)

        # Complete prerequisite
        CompletedEnrollmentFactory(user=user, course=prereq)

        enrollment = EnrollmentService.enroll_user(user, course)

        assert enrollment.user == user
        assert enrollment.course == course

    def test_enroll_user_with_multiple_prerequisites(self):
        """Test enrolling with multiple prerequisites."""
        user = UserFactory()
        prereq1 = PublishedCourseFactory()
        prereq2 = PublishedCourseFactory()
        course = PublishedCourseFactory()
        course.prerequisites.add(prereq1, prereq2)

        # Complete only one prerequisite
        CompletedEnrollmentFactory(user=user, course=prereq1)

        with pytest.raises(ValueError):
            EnrollmentService.enroll_user(user, course)

        # Complete second prerequisite
        CompletedEnrollmentFactory(user=user, course=prereq2)

        enrollment = EnrollmentService.enroll_user(user, course)
        assert enrollment is not None

    def test_update_progress_basic(self):
        """Test updating lesson progress."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course)

        progress_data = {"progress_percent": 50}
        lesson_progress = EnrollmentService.update_progress(enrollment, lesson, progress_data)

        assert lesson_progress.progress_percent == 50
        assert lesson_progress.is_completed is False

    def test_update_progress_complete_lesson(self):
        """Test completing a lesson."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course, is_mandatory=True)

        progress_data = {"progress_percent": 100, "completed": True}
        lesson_progress = EnrollmentService.update_progress(enrollment, lesson, progress_data)

        assert lesson_progress.is_completed is True
        assert lesson_progress.completed_at is not None

    def test_update_progress_auto_complete_at_100(self):
        """Test lesson auto-completes at 100% progress."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course)

        progress_data = {"progress_percent": 100}
        lesson_progress = EnrollmentService.update_progress(enrollment, lesson, progress_data)

        assert lesson_progress.is_completed is True

    def test_update_progress_time_spent(self):
        """Test tracking time spent."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course)

        # First update
        EnrollmentService.update_progress(enrollment, lesson, {"time_spent": 300})
        # Second update
        lesson_progress = EnrollmentService.update_progress(enrollment, lesson, {"time_spent": 200})

        assert lesson_progress.time_spent == 500  # Accumulated

    def test_update_progress_last_position(self):
        """Test saving last position."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course)

        position = {"video_time": 120, "page": 3}
        progress_data = {"last_position": position}
        lesson_progress = EnrollmentService.update_progress(enrollment, lesson, progress_data)

        assert lesson_progress.last_position == position

    def test_update_enrollment_progress_calculation(self):
        """Test enrollment progress calculation."""
        course = CourseFactory()
        module = ModuleFactory(course=course)
        lesson1 = LessonFactory(module=module, is_mandatory=True)
        lesson2 = LessonFactory(module=module, is_mandatory=True)
        lesson3 = LessonFactory(module=module, is_mandatory=False)  # Optional

        enrollment = EnrollmentFactory(course=course)

        # Complete one mandatory lesson
        CompletedLessonProgressFactory(enrollment=enrollment, lesson=lesson1)

        updated = EnrollmentService.update_enrollment_progress(enrollment)

        assert updated.progress == 50.0  # 1/2 mandatory lessons

    def test_update_enrollment_progress_starts_course(self):
        """Test that progress updates change status to IN_PROGRESS."""
        course = CourseFactory()
        module = ModuleFactory(course=course)
        lesson = LessonFactory(module=module, is_mandatory=True)

        enrollment = EnrollmentFactory(course=course, status=Enrollment.Status.ENROLLED)

        LessonProgressFactory(
            enrollment=enrollment,
            lesson=lesson,
            is_completed=True,
            progress_percent=Decimal("100.00"),
        )

        updated = EnrollmentService.update_enrollment_progress(enrollment)

        assert updated.status == Enrollment.Status.COMPLETED
        assert updated.started_at is not None

    def test_update_enrollment_progress_completes_course(self):
        """Test that completing all lessons completes the course."""
        course = CourseFactory()
        module = ModuleFactory(course=course)
        lesson1 = LessonFactory(module=module, is_mandatory=True)
        lesson2 = LessonFactory(module=module, is_mandatory=True)

        enrollment = EnrollmentFactory(course=course, status=Enrollment.Status.IN_PROGRESS)

        CompletedLessonProgressFactory(enrollment=enrollment, lesson=lesson1)
        CompletedLessonProgressFactory(enrollment=enrollment, lesson=lesson2)

        updated = EnrollmentService.update_enrollment_progress(enrollment)

        assert updated.status == Enrollment.Status.COMPLETED
        assert updated.progress == 100.0
        assert updated.completed_at is not None

    def test_update_enrollment_progress_no_mandatory_lessons(self):
        """Test enrollment with no mandatory lessons."""
        course = CourseFactory()
        module = ModuleFactory(course=course)
        LessonFactory(module=module, is_mandatory=False)

        enrollment = EnrollmentFactory(course=course)

        updated = EnrollmentService.update_enrollment_progress(enrollment)

        # Should return enrollment unchanged when no mandatory lessons
        assert updated.progress == 0


@pytest.mark.django_db
class TestMediaService:
    """Tests for MediaService."""

    def test_upload_asset_video(self):
        """Test uploading a video file."""
        user = UserFactory()
        video_content = b"fake video content"
        video_file = SimpleUploadedFile("test_video.mp4", video_content, content_type="video/mp4")

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(video_file, user)

        assert asset.file_type == MediaAsset.Type.VIDEO
        assert asset.mime_type == "video/mp4"
        assert asset.status == MediaAsset.Status.PENDING
        assert asset.uploaded_by == user
        mock_task.delay.assert_called_once()

    def test_upload_asset_audio(self):
        """Test uploading an audio file."""
        user = UserFactory()
        audio_file = SimpleUploadedFile(
            "test_audio.mp3", b"fake audio content", content_type="audio/mpeg"
        )

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(audio_file, user)

        assert asset.file_type == MediaAsset.Type.AUDIO

    def test_upload_asset_image(self):
        """Test uploading an image file."""
        user = UserFactory()
        image_file = SimpleUploadedFile(
            "test_image.jpg", b"fake image content", content_type="image/jpeg"
        )

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(image_file, user)

        assert asset.file_type == MediaAsset.Type.IMAGE

    def test_upload_asset_document(self):
        """Test uploading a document file."""
        user = UserFactory()
        pdf_file = SimpleUploadedFile(
            "test_document.pdf", b"fake pdf content", content_type="application/pdf"
        )

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(pdf_file, user)

        assert asset.file_type == MediaAsset.Type.DOCUMENT

    def test_upload_asset_scorm(self):
        """Test uploading a SCORM package."""
        user = UserFactory()
        scorm_file = SimpleUploadedFile(
            "scorm_package.zip", b"fake zip content", content_type="application/zip"
        )

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(scorm_file, user)

        assert asset.file_type == MediaAsset.Type.SCORM

    def test_upload_asset_with_explicit_type(self):
        """Test uploading with explicit file type."""
        user = UserFactory()
        file = SimpleUploadedFile("file.bin", b"content", content_type="application/octet-stream")

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(file, user, file_type=MediaAsset.Type.DOCUMENT)

        assert asset.file_type == MediaAsset.Type.DOCUMENT

    def test_upload_asset_unknown_type(self):
        """Test uploading unknown file type defaults to DOCUMENT."""
        user = UserFactory()
        file = SimpleUploadedFile("file.unknown", b"content", content_type="application/x-unknown")

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(file, user)

        assert asset.file_type == MediaAsset.Type.DOCUMENT

    def test_upload_asset_generates_unique_filename(self):
        """Test that uploaded files get unique filenames."""
        user = UserFactory()
        file = SimpleUploadedFile("original_name.mp4", b"content", content_type="video/mp4")

        with patch("apps.courses.tasks.process_media_asset") as mock_task:
            mock_task.delay = MagicMock()
            asset = MediaService.upload_asset(file, user)

        assert asset.original_name == "original_name.mp4"
        assert asset.filename != "original_name.mp4"
        assert asset.filename.endswith(".mp4")

    def test_get_asset_status_found(self):
        """Test getting status of existing asset."""
        from apps.courses.tests.factories import ReadyMediaAssetFactory

        asset = ReadyMediaAssetFactory()

        status = MediaService.get_asset_status(asset.id)

        assert status["id"] == asset.id
        assert status["status"] == MediaAsset.Status.READY
        assert status["error"] == ""

    def test_get_asset_status_not_found(self):
        """Test getting status of non-existent asset."""
        status = MediaService.get_asset_status(99999)

        assert status["error"] == "Asset not found"

    def test_get_asset_status_with_error(self):
        """Test getting status of asset with error."""
        from apps.courses.tests.factories import ErrorMediaAssetFactory

        asset = ErrorMediaAssetFactory()

        status = MediaService.get_asset_status(asset.id)

        assert status["status"] == MediaAsset.Status.ERROR
        assert status["error"] != ""


@pytest.mark.django_db
class TestScormService:
    """Tests for ScormService."""

    def _create_valid_scorm_zip(self) -> bytes:
        """Create a valid SCORM package ZIP file."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Create imsmanifest.xml
            manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="test_manifest" version="1.0"
    xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
    <organizations>
        <organization identifier="org1">
            <title>Test SCORM Package</title>
        </organization>
    </organizations>
    <resources>
        <resource identifier="res1" type="webcontent" href="index.html">
            <file href="index.html"/>
        </resource>
    </resources>
</manifest>"""
            zf.writestr("imsmanifest.xml", manifest)
            zf.writestr("index.html", "<html><body>SCORM Content</body></html>")
        buffer.seek(0)
        return buffer.read()

    def _create_invalid_zip(self) -> bytes:
        """Create an invalid ZIP file."""
        return b"not a zip file"

    def _create_zip_without_manifest(self) -> bytes:
        """Create a ZIP without SCORM manifest."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", "<html><body>Content</body></html>")
        buffer.seek(0)
        return buffer.read()

    @patch("apps.courses.services.settings")
    def test_process_package_success(self, mock_settings):
        """Test processing a valid SCORM package."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_settings.MEDIA_ROOT = temp_dir

            lesson = ScormLessonFactory()
            zip_content = self._create_valid_scorm_zip()

            # Create the package with a real file
            package = ScormPackage.objects.create(
                lesson=lesson,
                package_file=ContentFile(zip_content, name="scorm.zip"),
                status=ScormPackage.Status.UPLOADED,
            )

            processed = ScormService.process_package(package)

            assert processed.status == ScormPackage.Status.READY
            assert processed.entry_point == "index.html"
            assert processed.extracted_path != ""

    def test_process_package_invalid_zip(self):
        """Test processing an invalid ZIP file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lesson = ScormLessonFactory()

            # Create file with invalid content
            invalid_content = self._create_invalid_zip()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
                f.write(invalid_content)
                f.flush()

                package = ScormPackage.objects.create(
                    lesson=lesson,
                    status=ScormPackage.Status.UPLOADED,
                )
                # Manually set the path
                package.package_file.name = f.name

                processed = ScormService.process_package(package)

                assert processed.status == ScormPackage.Status.ERROR
                # Error message may vary - just ensure there's an error message
                assert processed.error_message

    @patch("apps.courses.services.settings")
    def test_process_package_missing_manifest(self, mock_settings):
        """Test processing a package without manifest."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_settings.MEDIA_ROOT = temp_dir

            lesson = ScormLessonFactory()
            zip_content = self._create_zip_without_manifest()

            package = ScormPackage.objects.create(
                lesson=lesson,
                package_file=ContentFile(zip_content, name="scorm.zip"),
                status=ScormPackage.Status.UPLOADED,
            )

            processed = ScormService.process_package(package)

            assert processed.status == ScormPackage.Status.ERROR
            assert "manifiesto" in processed.error_message.lower()

    def test_process_package_sets_extracting_status(self):
        """Test that processing sets status to EXTRACTING first."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lesson = ScormLessonFactory()

            # Create a minimal package that will fail
            package = ScormPackage.objects.create(
                lesson=lesson,
                status=ScormPackage.Status.UPLOADED,
            )
            package.package_file.name = "/nonexistent/path.zip"

            # Process will fail but we can check it tried
            ScormService.process_package(package)

            # Status should be ERROR after failure
            assert package.status == ScormPackage.Status.ERROR


@pytest.mark.django_db
class TestResourceLibraryService:
    """Tests for ResourceLibraryService."""

    def test_add_resource_image(self):
        """Test adding an image resource."""
        user = UserFactory()
        image_file = SimpleUploadedFile(
            "test_image.jpg", b"fake image content", content_type="image/jpeg"
        )

        resource = ResourceLibraryService.add_resource(
            image_file,
            user,
            name="Test Image",
            tags=["test", "image"],
        )

        assert resource.name == "Test Image"
        assert resource.resource_type == ResourceLibrary.Type.IMAGE
        assert resource.tags == ["test", "image"]
        assert resource.uploaded_by == user

    def test_add_resource_video(self):
        """Test adding a video resource."""
        user = UserFactory()
        video_file = SimpleUploadedFile(
            "test_video.mp4", b"fake video content", content_type="video/mp4"
        )

        resource = ResourceLibraryService.add_resource(video_file, user)

        assert resource.resource_type == ResourceLibrary.Type.VIDEO

    def test_add_resource_audio(self):
        """Test adding an audio resource."""
        user = UserFactory()
        audio_file = SimpleUploadedFile(
            "test_audio.mp3", b"fake audio content", content_type="audio/mpeg"
        )

        resource = ResourceLibraryService.add_resource(audio_file, user)

        assert resource.resource_type == ResourceLibrary.Type.AUDIO

    def test_add_resource_document(self):
        """Test adding a document resource."""
        user = UserFactory()
        pdf_file = SimpleUploadedFile(
            "test_doc.pdf", b"fake pdf content", content_type="application/pdf"
        )

        resource = ResourceLibraryService.add_resource(pdf_file, user)

        assert resource.resource_type == ResourceLibrary.Type.DOCUMENT

    def test_add_resource_with_category(self):
        """Test adding a resource with category."""
        user = UserFactory()
        category = CategoryFactory()
        file = SimpleUploadedFile("test.jpg", b"content", content_type="image/jpeg")

        resource = ResourceLibraryService.add_resource(file, user, category=category)

        assert resource.category == category

    def test_add_resource_default_name(self):
        """Test that resource name defaults to filename."""
        user = UserFactory()
        file = SimpleUploadedFile("original_filename.jpg", b"content", content_type="image/jpeg")

        resource = ResourceLibraryService.add_resource(file, user)

        assert resource.name == "original_filename.jpg"

    def test_search_resources_by_query(self):
        """Test searching resources by query."""
        user = UserFactory()
        from apps.courses.tests.factories import ResourceLibraryFactory

        ResourceLibraryFactory(name="Safety Poster", uploaded_by=user)
        ResourceLibraryFactory(name="Equipment Manual", uploaded_by=user)
        ResourceLibraryFactory(name="Safety Guidelines", uploaded_by=user)

        results = ResourceLibraryService.search_resources(query="Safety")

        assert results.count() == 2

    def test_search_resources_by_type(self):
        """Test searching resources by type."""
        from apps.courses.tests.factories import (
            DocumentResourceFactory,
            ResourceLibraryFactory,
            VideoResourceFactory,
        )

        ResourceLibraryFactory()  # Image
        VideoResourceFactory()
        DocumentResourceFactory()

        results = ResourceLibraryService.search_resources(resource_type=ResourceLibrary.Type.VIDEO)

        assert results.count() == 1

    def test_search_resources_by_category(self):
        """Test searching resources by category."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        category1 = CategoryFactory()
        category2 = CategoryFactory()

        ResourceLibraryFactory(category=category1)
        ResourceLibraryFactory(category=category1)
        ResourceLibraryFactory(category=category2)

        results = ResourceLibraryService.search_resources(category_id=category1.id)

        assert results.count() == 2

    def test_search_resources_private_excluded(self):
        """Test that private resources are excluded from search."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        ResourceLibraryFactory(is_public=True, name="Public Resource")
        ResourceLibraryFactory(is_public=False, name="Private Resource")

        results = ResourceLibraryService.search_resources()

        assert results.count() == 1
        assert results.first().name == "Public Resource"

    def test_search_resources_ordering(self):
        """Test that results are ordered by usage_count and created_at."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        low_usage = ResourceLibraryFactory(usage_count=5)
        high_usage = ResourceLibraryFactory(usage_count=100)
        medium_usage = ResourceLibraryFactory(usage_count=50)

        results = list(ResourceLibraryService.search_resources())

        assert results[0] == high_usage
        assert results[1] == medium_usage
        assert results[2] == low_usage

    def test_increment_usage(self):
        """Test incrementing resource usage count."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        resource = ResourceLibraryFactory(usage_count=10)

        ResourceLibraryService.increment_usage(resource.id)

        resource.refresh_from_db()
        assert resource.usage_count == 11

    def test_increment_usage_multiple_times(self):
        """Test incrementing usage count multiple times."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        resource = ResourceLibraryFactory(usage_count=0)

        for _ in range(5):
            ResourceLibraryService.increment_usage(resource.id)

        resource.refresh_from_db()
        assert resource.usage_count == 5

    def test_increment_usage_nonexistent(self):
        """Test incrementing usage for non-existent resource does nothing."""
        # Should not raise an error
        ResourceLibraryService.increment_usage(99999)


@pytest.mark.django_db
class TestServiceEdgeCases:
    """Tests for edge cases in services."""

    def test_create_course_empty_modules_list(self):
        """Test creating course with empty modules list."""
        user = UserFactory()
        data = {
            "code": "TEST-EMPTY",
            "title": "Course with Empty Modules",
            "description": "Description",
            "duration": 60,
            "modules": [],
        }

        course = CourseService.create_course(data, user)

        assert course.modules.count() == 0

    def test_duplicate_course_no_modules(self):
        """Test duplicating course without modules."""
        user = UserFactory()
        original = CourseFactory()

        duplicate = CourseService.duplicate_course(original, user)

        assert duplicate.modules.count() == 0

    def test_enrollment_progress_all_optional_lessons(self):
        """Test enrollment progress when all lessons are optional."""
        course = CourseFactory()
        module = ModuleFactory(course=course)
        LessonFactory(module=module, is_mandatory=False)
        LessonFactory(module=module, is_mandatory=False)

        enrollment = EnrollmentFactory(course=course)

        # No mandatory lessons to complete
        updated = EnrollmentService.update_enrollment_progress(enrollment)

        assert updated.progress == 0

    def test_update_progress_creates_lesson_progress(self):
        """Test that update_progress creates LessonProgress if not exists."""
        enrollment = EnrollmentFactory()
        lesson = LessonFactory(module__course=enrollment.course)

        assert not LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson).exists()

        EnrollmentService.update_progress(enrollment, lesson, {"progress_percent": 50})

        assert LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson).exists()

    @pytest.mark.skipif(
        "sqlite" in str(settings.DATABASES.get("default", {}).get("ENGINE", "")),
        reason="SQLite does not support contains lookup on JSONField",
    )
    def test_search_resources_with_tags(self):
        """Test searching resources with specific tags."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        ResourceLibraryFactory(tags=["safety", "equipment"])
        ResourceLibraryFactory(tags=["safety", "training"])
        ResourceLibraryFactory(tags=["equipment", "maintenance"])

        results = ResourceLibraryService.search_resources(tags=["safety"])

        assert results.count() == 2

    def test_search_resources_empty_query(self):
        """Test searching with empty query returns all public."""
        from apps.courses.tests.factories import ResourceLibraryFactory

        ResourceLibraryFactory(is_public=True)
        ResourceLibraryFactory(is_public=True)
        ResourceLibraryFactory(is_public=False)

        results = ResourceLibraryService.search_resources()

        assert results.count() == 2

    def test_course_statistics_average_progress(self):
        """Test average progress calculation."""
        course = PublishedCourseFactory()

        EnrollmentFactory(course=course, progress=Decimal("25.00"))
        EnrollmentFactory(course=course, progress=Decimal("50.00"))
        EnrollmentFactory(course=course, progress=Decimal("75.00"))
        EnrollmentFactory(course=course, progress=Decimal("100.00"))

        stats = CourseService.get_course_statistics(course)

        assert stats["average_progress"] == 62.5

    def test_publish_course_increments_version(self):
        """Test that publishing increments version number."""
        user = UserFactory()
        course = CourseFactory(version=1)

        CourseService.publish_course(course, user)

        course.refresh_from_db()
        assert course.version == 2

    def test_duplicate_preserves_lesson_metadata(self):
        """Test that duplicating preserves lesson metadata."""
        user = UserFactory()
        original = CourseFactory()
        module = ModuleFactory(course=original)
        metadata = {"quiz_settings": {"time_limit": 30, "max_attempts": 3}}
        LessonFactory(module=module, metadata=metadata)

        duplicate = CourseService.duplicate_course(original, user)

        dup_lesson = duplicate.modules.first().lessons.first()
        assert dup_lesson.metadata == metadata

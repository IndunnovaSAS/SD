"""Management command to clear all courses and related data."""

from django.core.management.base import BaseCommand

from apps.courses.models import Category, Course, Enrollment


class Command(BaseCommand):
    help = "Delete all courses, modules, lessons, enrollments and categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        courses_count = Course.objects.count()
        enrollments_count = Enrollment.objects.count()
        categories_count = Category.objects.count()

        self.stdout.write(f"Courses: {courses_count}")
        self.stdout.write(f"Enrollments: {enrollments_count}")
        self.stdout.write(f"Categories: {categories_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing deleted."))
            return

        if courses_count == 0 and categories_count == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to delete."))
            return

        Enrollment.objects.all().delete()
        deleted = Course.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted[0]} objects (cascade).")
        )

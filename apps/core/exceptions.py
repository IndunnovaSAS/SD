"""
Custom exceptions for the SD LMS application.

This module provides specific exception classes to improve error handling,
logging, and debugging across the application.
"""


class SDBaseException(Exception):
    """Base exception for all SD LMS custom exceptions."""

    default_message = "Ha ocurrido un error en el sistema."
    default_code = "sd_error"

    def __init__(self, message: str = None, code: str = None, details: dict = None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return self.message


# Authentication and Authorization Exceptions
class AuthenticationError(SDBaseException):
    """Exception raised for authentication failures."""

    default_message = "Error de autenticacion."
    default_code = "authentication_error"


class TokenError(AuthenticationError):
    """Exception raised for token-related errors."""

    default_message = "Token invalido o expirado."
    default_code = "token_error"


class TokenBlacklistedError(TokenError):
    """Exception raised when a token has been blacklisted."""

    default_message = "El token ha sido revocado."
    default_code = "token_blacklisted"


class TokenExpiredError(TokenError):
    """Exception raised when a token has expired."""

    default_message = "El token ha expirado."
    default_code = "token_expired"


# Course and Learning Exceptions
class CourseError(SDBaseException):
    """Base exception for course-related errors."""

    default_message = "Error en el curso."
    default_code = "course_error"


class EnrollmentError(CourseError):
    """Exception raised for enrollment-related errors."""

    default_message = "Error en la inscripcion."
    default_code = "enrollment_error"


class ScormProcessingError(CourseError):
    """Exception raised when SCORM package processing fails."""

    default_message = "Error procesando el paquete SCORM."
    default_code = "scorm_processing_error"


class MediaProcessingError(CourseError):
    """Exception raised when media asset processing fails."""

    default_message = "Error procesando el archivo multimedia."
    default_code = "media_processing_error"


class PackageGenerationError(CourseError):
    """Exception raised when course package generation fails."""

    default_message = "Error generando el paquete del curso."
    default_code = "package_generation_error"


# Certification Exceptions
class CertificationError(SDBaseException):
    """Base exception for certification-related errors."""

    default_message = "Error en la certificacion."
    default_code = "certification_error"


class CertificateGenerationError(CertificationError):
    """Exception raised when certificate generation fails."""

    default_message = "Error generando el certificado."
    default_code = "certificate_generation_error"


class CertificateValidationError(CertificationError):
    """Exception raised for certificate validation errors."""

    default_message = "Error validando el certificado."
    default_code = "certificate_validation_error"


class QRCodeGenerationError(CertificationError):
    """Exception raised when QR code generation fails."""

    default_message = "Error generando el codigo QR."
    default_code = "qr_generation_error"


class PDFGenerationError(CertificationError):
    """Exception raised when PDF generation fails."""

    default_message = "Error generando el PDF."
    default_code = "pdf_generation_error"


# Notification Exceptions
class NotificationError(SDBaseException):
    """Base exception for notification-related errors."""

    default_message = "Error en las notificaciones."
    default_code = "notification_error"


class NotificationDeliveryError(NotificationError):
    """Exception raised when notification delivery fails."""

    default_message = "Error enviando la notificacion."
    default_code = "notification_delivery_error"


class PushNotificationError(NotificationError):
    """Exception raised for push notification errors."""

    default_message = "Error enviando notificacion push."
    default_code = "push_notification_error"


class EmailDeliveryError(NotificationError):
    """Exception raised for email delivery errors."""

    default_message = "Error enviando correo electronico."
    default_code = "email_delivery_error"


class SMSDeliveryError(NotificationError):
    """Exception raised for SMS delivery errors."""

    default_message = "Error enviando SMS."
    default_code = "sms_delivery_error"


# Learning Path Exceptions
class LearningPathError(SDBaseException):
    """Base exception for learning path-related errors."""

    default_message = "Error en la ruta de aprendizaje."
    default_code = "learning_path_error"


class PathAssignmentError(LearningPathError):
    """Exception raised for path assignment errors."""

    default_message = "Error asignando la ruta de aprendizaje."
    default_code = "path_assignment_error"


# File Processing Exceptions
class FileProcessingError(SDBaseException):
    """Base exception for file processing errors."""

    default_message = "Error procesando el archivo."
    default_code = "file_processing_error"


class InvalidFileError(FileProcessingError):
    """Exception raised for invalid file errors."""

    default_message = "El archivo no es valido."
    default_code = "invalid_file_error"


class ImageProcessingError(FileProcessingError):
    """Exception raised when image processing fails."""

    default_message = "Error procesando la imagen."
    default_code = "image_processing_error"


# External Service Exceptions
class ExternalServiceError(SDBaseException):
    """Base exception for external service errors."""

    default_message = "Error en servicio externo."
    default_code = "external_service_error"


class FFmpegError(ExternalServiceError):
    """Exception raised for FFmpeg processing errors."""

    default_message = "Error en el procesamiento de video/audio."
    default_code = "ffmpeg_error"


class WebPushError(ExternalServiceError):
    """Exception raised for web push service errors."""

    default_message = "Error en el servicio de notificaciones push."
    default_code = "webpush_error"

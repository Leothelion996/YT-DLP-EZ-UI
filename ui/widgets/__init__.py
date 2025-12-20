"""
UI widgets package for YT-DLP EZ-UI.
Contains all custom widgets used in the application.
"""

from .link_input import LinkInputWidget
from .link_list import LinkListWidget
from .options import OptionsWidget
from .output_select import OutputSelectWidget
from .progress_widget import ProgressWidget
from .log_viewer import LogViewer
from .beets_options import BeetsOptionsWidget
from .file_rename_dialog import FileRenameDialog  # v3.0
from .manual_metadata_dialog import ManualMetadataDialog  # v4.0
from .folder_drop_widget import FolderDropWidget  # v4.0
from .folder_processing_options_dialog import FolderProcessingOptionsDialog  # v4.0
from .header_widget import HeaderWidget  # v5.0
from .preferences_dialog import PreferencesDialog  # v5.0
from .csv_processor_dialog import CSVProcessorDialog  # v5.0
from .metadata_editor_widget import MetadataEditorWidget  # v5.0
from .folder_metadata_review_dialog import FolderMetadataReviewDialog  # v5.1

__all__ = ['LinkInputWidget', 'LinkListWidget', 'OptionsWidget', 'OutputSelectWidget', 'ProgressWidget', 'LogViewer', 'BeetsOptionsWidget', 'FileRenameDialog', 'ManualMetadataDialog', 'FolderDropWidget', 'FolderProcessingOptionsDialog', 'HeaderWidget', 'PreferencesDialog', 'CSVProcessorDialog', 'MetadataEditorWidget', 'FolderMetadataReviewDialog']

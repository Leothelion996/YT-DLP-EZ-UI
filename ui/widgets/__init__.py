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

__all__ = ['LinkInputWidget', 'LinkListWidget', 'OptionsWidget', 'OutputSelectWidget', 'ProgressWidget', 'LogViewer', 'BeetsOptionsWidget', 'FileRenameDialog', 'ManualMetadataDialog', 'FolderDropWidget', 'FolderProcessingOptionsDialog']

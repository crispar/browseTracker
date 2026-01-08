"""
Browser Link Tracker - Main entry point.
Personal link management tool that tracks browsing history across multiple browsers.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path for imports
if getattr(sys, 'frozen', False):
    # If frozen (compiled), we're in the executable
    base_path = sys._MEIPASS
else:
    # If not frozen, we're running from source
    base_path = Path(__file__).parent
    os.environ['LINK_TRACKER_DEV'] = '1'

# Add base path to system path for imports
sys.path.insert(0, str(base_path))


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path('logs') if os.environ.get('LINK_TRACKER_DEV') else Path(os.environ.get('APPDATA', '.')) / 'LinkTracker' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / 'linktracker.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Browser Link Tracker starting...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)


def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)

        # Import after logging is configured
        from gui.main_window import MainWindow

        # Create and run application
        logger.info("Creating main window...")
        app = MainWindow()

        logger.info("Starting GUI event loop...")
        app.run()

        logger.info("Application closed normally")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please ensure all dependencies are installed:")
        logger.error("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

        # Show error dialog if tkinter is available
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred:\n\n{e}\n\nPlease check the log file for details."
            )
            root.destroy()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
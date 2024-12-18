from controllers.controller import DynamicSlicingController
from ryu.base import app_manager

if __name__ == "__main__":
    # This ensures Ryu correctly recognizes and runs your app
    app_manager.AppManager.run_apps([DynamicSlicingController])

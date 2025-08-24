# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from app import create_app, socketio

app = create_app('demo')  # Pass 'demo' to use DemoConfig

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

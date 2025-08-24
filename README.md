# unified_communication_platform
A Flask-based platform for unified communication, supporting chat, calls, contacts, voicemail, and more.

## Features

- User authentication (demo and production modes)
- Role-based access (Admin, Agent, User)
- Chat, phone, voicemail, and contact management
- Real-time communication via SIP Trunk
- PostgreSQL and sqlite database support
- Flask-Migrate for database migrations

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. **Clone the repository:**
   ```
   git clone https://github.com/abubackersiddiqm/unified_communication_platform.git
   cd unified_communication_platform
   ```

2. **Set up Python environment:**
   ```
   python -m venv env
   env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file inside the `backend` folder:

   ``` env
   # Use PostgreSQL
   DATABASE_URL=postgresql://username:dbpassword@localhost:5432/dbname

   # Secret key for security
   SECRET_KEY=your_secret_key
   ```

   > **Note:** If you are using **SQLite**, leave the `DATABASE_URL` value
   > empty, e.g. 
   >
   > ``` env
   > DATABASE_URL=
   > ```

4. **Initialize the database:**
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. **Run the application:**
   ```
   python backend/run.py
   ```

   The app will be available at [http://localhost:5000](http://localhost:5000).

### Demo Credentials

If running in demo mode, use:
- **Username:** `demo`
- **Password:** `demo123`


## Troubleshooting

- **Database connection errors:**  
  Ensure PostgreSQL is running and credentials in `.env` are correct.

- **`psql` not recognized:**  
  Add PostgreSQL's `bin` directory to your system PATH.

- **Migration errors:**  
  Make sure Flask-Migrate is installed and initialized in your code.

## License

MIT License

Copyright (c) 2025 Abubacker Siddiq

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


---

For more details, see the code comments and documentation in each module.
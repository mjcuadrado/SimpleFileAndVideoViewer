OposicionesWeb
OposicionesWeb is a Flask-based web application designed to help users visualize videos and files (such as PDFs) organized in a directory structure. The app scans a specified directory (/folders by default) to display folders, subfolders, and their associated files in a user-friendly interface. It supports features like video playback, PDF viewing, user authentication, and admin functionalities for managing content.

This app is particularly useful for organizing and accessing educational or professional materials stored in a folder-based structure.

Features
Folder Visualization: Automatically scans a directory (/folders) to display folders and their subfolders.
File Support: Supports video files (.mp4) for playback and documents (.pdf) for viewing and downloading.
User Authentication: Includes login/logout functionality to secure access to content.
Admin Features: Admins can manage users, videos, and view logs.
Responsive Design: Built with Bootstrap for a mobile-friendly interface.
Prerequisites
Before setting up the app, ensure you have the following installed:

Docker
Docker Compose
A directory containing your files (videos and PDFs) structured as follows:
text

Contraer

Ajuste

Copiar
/path/to/folders/
├── Folder1/
│   ├── video1.mp4
│   ├── document1.pdf
│   └── Subfolder/
│       ├── video2.mp4
│       └── document2.pdf
├── Folder2/
│   ├── video3.mp4
│   └── document3.pdf
Setup with Docker Compose
Follow these steps to get the app running using Docker Compose.

1. Clone the Repository
Clone this repository to your local machine:

bash

Contraer

Ajuste

Copiar
git clone https://github.com/yourusername/oposicionesweb.git
cd oposicionesweb
2. Create a .env File
Create a .env file in the root directory of the project to define the necessary environment variables. Below is an example .env file with the required variables:

env

Contraer

Ajuste

Copiar
# Flask app configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database configuration
DATABASE_URL=postgresql://user:password@db:5432/oposicionesdb

# Directory for folder files (this should match the volume mapping in docker-compose.yml)
CURSOS_DIR=/folders

# Maximum queue size for processing (optional, default is 5)
MAX_QUEUE_SIZE=5
Explanation of Environment Variables:
SECRET_KEY: A secret key for Flask to secure sessions and other cryptographic operations. Replace your-secret-key-here with a secure, random string.
FLASK_ENV: Set to production for a production environment or development for debugging.
DATABASE_URL: The connection string for the PostgreSQL database. The format is postgresql://user:password@host:port/dbname. Adjust user, password, db, and oposicionesdb as needed.
CURSOS_DIR: The directory where the app will look for folder files. This should match the volume mapping in docker-compose.yml. Default is /folders.
MAX_QUEUE_SIZE: The maximum number of items in the processing queue (optional, defaults to 5).
3. Set Up docker-compose.yml
Below is an example docker-compose.yml file to run the app with a PostgreSQL database. Create or update this file in the root directory of the project:

yaml

Contraer

Ajuste

Copiar
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=${FLASK_ENV}
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - CURSOS_DIR=${CURSOS_DIR}
      - MAX_QUEUE_SIZE=${MAX_QUEUE_SIZE}
    volumes:
      - /path/to/folders:/folders
    depends_on:
      - db
    networks:
      - app-network

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=oposicionesdb
    volumes:
      - db-data:/var/lib/postgresql/data
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  db-data:
Explanation of docker-compose.yml:
web service:
Builds the Flask app from the Dockerfile in the current directory.
Maps port 5000 on the host to port 5000 in the container.
Loads environment variables from the .env file.
Mounts the local directory /path/to/folders (where your files are stored) to /folders in the container. Replace /path/to/folders with the actual path to your files.
Depends on the db service to ensure the database is running before the app starts.
db service:
Uses the official PostgreSQL 13 image.
Sets up the database with the user, password, and database name specified in the environment variables.
Persists database data using a named volume (db-data).
networks:
Creates a bridge network (app-network) for communication between the web and db services.
4. Build and Run the App
Run the following command to build and start the app:

bash

Contraer

Ajuste

Copiar
docker-compose up -d --build
The -d flag runs the containers in the background.
The --build flag ensures the app is rebuilt if there are changes.
5. Access the App
Once the containers are running, you can access the app at:

text

Contraer

Ajuste

Copiar
http://localhost:5000
Log in with your credentials (if you haven't set up users yet, you may need to create an admin user directly in the database).
The app will scan the /folders directory and display the available folders in the navigation menu.
6. Stop the App
To stop the app, run:

bash

Contraer

Ajuste

Copiar
docker-compose down
If you want to remove the database volume as well (this will delete all database data), add the -v flag:

bash

Contraer

Ajuste

Copiar
docker-compose down -v
Directory Structure for Folders
The app expects files to be organized in the following structure:

text

Contraer

Ajuste

Copiar
/folders/
├── Folder1/
│   ├── video1.mp4
│   ├── document1.pdf
│   └── Subfolder/
│       ├── video2.mp4
│       └── document2.pdf
├── Folder2/
│   ├── video3.mp4
│   └── document3.pdf
Top-level directories (e.g., Folder1, Folder2) are treated as main folders.
Subdirectories (e.g., Subfolder) are treated as subfolders within a main folder.
Files:
.mp4 files are displayed as videos with a player.
.pdf files are displayed as downloadable links.
Ensure that the directory you mount in the docker-compose.yml (/path/to/folders) matches this structure.

Troubleshooting
Folders not showing up:
Verify that the /path/to/folders directory is correctly mounted to /folders in the container.
Check the logs for errors:
bash

Contraer

Ajuste

Copiar
docker-compose logs web
Ensure the directory structure matches the expected format.
Database connection issues:
Confirm that the DATABASE_URL in the .env file matches the credentials in the db service in docker-compose.yml.
Ensure the db service is running before the web service starts.
Permission issues:
Ensure the web container has read permissions for the /folders directory:
bash

Contraer

Ajuste

Copiar
chmod -R 755 /path/to/folders
Contributing
Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

License
This project is licensed under the MIT License. See the LICENSE file for details.

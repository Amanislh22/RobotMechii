# RobotMechi

An autonomous robot that follows a path specified by an image.

## Structure
- `backend/`: FastAPI backend for image processing and command generation.
- `frontend/`: Angular frontend for user interaction.
- `robot/`: STM32F4 firmware for the PathFollower.
- `docs/`: Documentation.

## Setup
See `docs/setup.md` for detailed instructions.

## Usage
1. Start the backend server.
2. Start the frontend app.
3. Upload a path image via the frontend.
4. Send the generated commands to the robot.

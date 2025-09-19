# Smart Image Renamer

Image Organizer App

This is a web application built with Streamlit that provides a user-friendly interface to organize and rename image files. It automates the process of matching prompts from a text file to image files in a directory and saving the organized images to a new location.

Features
User-Friendly Interface: An easy-to-use web form to configure file paths and options.

Flexible Matching: Automatically matches image filenames to prompts using both numeric IDs and URL stems.

Progress Indicator: A real-time progress bar to show the status of the file processing.

Detailed Reporting: Generates a comprehensive report.txt file that logs all processed, missing, and unused files.

Safe Operations: Includes a "Dry Run" mode to simulate the process without making any changes to your files.

Prerequisites
To run this application, you must have Python and the streamlit library installed. You can install it using pip:

pip install streamlit

How to Use
Follow these steps to set up and run the application:

Prepare your files:

Create a text file containing your prompts (e.g., prompts.txt). Each prompt should be on a new line and can include a numeric ID or a URL to help with matching.

Create a folder containing the images you want to organize (e.g., images/).

Run the App:

Save this script as app.py.

Open your terminal or command prompt and navigate to the directory where you saved app.py.

Run the following command:

streamlit run app.py

Your default web browser will open and display the application's interface.

Configure and Run:

In the app, enter the paths to your prompts.txt file, your images directory, and the desired output directory.

Adjust the Image filename prefix and extension as needed.

Select the Move files option if you want to move the original files instead of copying them.

Select the Dry Run option to test the script without modifying any files.

Click the Run Image Organizer button to start the process.

After the process is complete, the application will display a summary of its actions on the page and save a detailed report.txt file to your specified output directory.

import os  # Importing the os module to interact with the operating system
import re  # Importing the re module for regular expression operations
import hashlib  # Importing hashlib for hashing passwords
import time  # Importing time for implementing delays
import PyPDF2 as pdf  # Importing PyPDF2 for reading PDF files
import streamlit as st  # Importing Streamlit for building the web application
from dotenv import load_dotenv  # Importing load_dotenv to load environment variables from a .env file
import google.generativeai as genai  # Importing the Google Generative AI library
import io  # Importing io for handling byte streams
from reportlab.lib.pagesizes import letter  # Importing letter page size for PDF generation
from reportlab.pdfgen import canvas  # Importing canvas for PDF generation

# Load environment variables from a .env file
load_dotenv()
# Configure the Google Generative AI API with the API key from environment variables
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Initialize the generative model
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Set up the Streamlit page configuration
st.set_page_config(
    page_title="Smart Application Tracking System",  # Title of the web page
    page_icon=":robot:",  # Icon displayed in the browser tab
    layout="wide"  # Layout of the page
)

# CSS styling for the background and UI elements
page_bg_img = """
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: url("https://e0.pxfuel.com/wallpapers/219/656/desktop-wallpaper-purple-color-background-best-for-your-mobile-tablet-explore-color-cool-color-colored-background-one-color-aesthetic-one-color.jpg");
    background-size: cover;  # Cover the entire background
    background-position: top left;  # Position the background image
    background-repeat: no-repeat;  # Do not repeat the background image
    background-attachment: local;  # Background scrolls with the page
}

[data-testid="stHeader"] {
    background: rgba(0,0,0,0);  # Transparent header background
}

[data-testid="stToolbar"] {
    right: 2rem;  # Position the toolbar
}

.stButton>button, .stDownloadButton>button {
    background-color: #4CAF50;  # Button background color
    color: white;  # Button text color
    padding: 10px 24px;  # Button padding
    border-radius: 8px;  # Rounded corners for the button
    border: none;  # No border for the button
    font-size: 16px;  # Button font size
}

.stButton>button:hover {
    background-color: #45a049;  # Button background color on hover
}
.ats-score {
    font-size: 2.5rem !important;
    color: #FFD700 !important;
    font-weight: bold;
    text-align: center;
    margin: 20px 0;
    padding: 15px;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 10px;
    border: 2px solid #4CAF50;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
}
</style>
"""

# Render the CSS styling in the Streamlit app
st.markdown(page_bg_img, unsafe_allow_html=True)

# Enhanced prompt template for the AI model
input_prompt = """
You are a skilled ATS (Application Tracking System) specialist. Analyze the resume against this job description:

RESUME:
{extracted_text}

JOB DESCRIPTION:
{jd}

Provide analysis STRICTLY in this format:

Job Description Match: [X]% (must be first line)
Missing Keywords: 
- [Keyword1]
- [Keyword2]
- [Keyword3]
Profile Summary:
- [Point1]
- [Point2]
- [Point3]
Improvement Suggestions:
- [Suggestion1]
- [Suggestion2]
- [Suggestion3]

The percentage MUST be calculated based on:
- Keyword matching (50% weight)
- Experience relevance (30% weight)
- Skills alignment (20% weight)
"""

# Function to extract text from a PDF file
def extract_text_from_pdf(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)  # Create a PDF reader object
    return " ".join([page.extract_text() for page in reader.pages])  # Extract text from each page

# Function to analyze the resume with retry logic for API calls
def analyze_resume_with_retry(extracted_text, jd, retries=5):
    for attempt in range(retries):  # Loop for the number of retries
        try:
            # Call the AI model to analyze the resume and job description
            response = model.generate_content(input_prompt.format(
                extracted_text=extracted_text, 
                jd=jd
            ))
            return response.text  # Return the analysis text
        except Exception as e:
            if "429" in str(e):  # Check for quota exceeded error
                wait_time = 2 ** attempt  # Calculate wait time for exponential backoff
                st.warning(f"Quota exceeded. Retrying in {wait_time} seconds...")  # Notify user
                time.sleep(wait_time)  # Wait before retrying
            else:
                st.error(f"AI Error: {str(e)}")  # Display other errors
                return None
    st.error("Failed to analyze resume after multiple attempts.")  # Notify user after retries
    return None

# Function to extract the match percentage from the analysis text
def extract_match_percentage(analysis_text):
    match = re.search(r"Job Description Match:\s*(\d{1,3})%", analysis_text)  # Regex to find match percentage
    if match:
        return int(match.group(1))  # Return the match percentage if found
    percentages = re.findall(r'\b(\d{1,3})%', analysis_text)  # Find all percentages in the text
    if percentages:
        return max(map(int, percentages))  # Return the maximum percentage found
    return 0  # Return 0 if no percentages found

# Function to hash passwords for secure storage
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()  # Hash the password using SHA-256

# Example user data (in a real application, use a database)
users = {
    "admin": hash_password("password"),  # Store hashed password for the admin user
}

# Function to display the login page for the HR portal
def login_page():
    st.title("Login to HR Portal")  # Title for the login page
    username = st.text_input("Username")  # Input field for username
    password = st.text_input("Password", type="password")  # Input field for password (hidden)

    if st.button("Login"):  # Button to submit login
        if username in users and users[username] == hash_password(password):  # Check credentials
            st.session_state.logged_in = True  # Set logged in state
            st.success("Login successful!")  # Notify user of successful login
        else:
            st.error("Invalid username or password. Please try again.")  # Notify user of failed login

# Function for the Job Seeker interface
def job_seeker_interface():
    st.title("Job Seeker Dashboard")  # Title for the Job Seeker dashboard
    st.subheader("Boost Your ATS Score")  # Subtitle for the dashboard
    
    # Session state initialization for storing analysis results
    session_defaults = {
        'analysis': None,
        'resume_file': None,
        'jd_text': ""
    }
    for key, val in session_defaults.items():
        if key not in st.session_state:  # Initialize session state if not already set
            st.session_state[key] = val

    # Input fields for job description and resume upload
    jd = st.text_area("Paste Job Description", 
                     height=200,
                     placeholder="Enter job description here...",
                     value=st.session_state.jd_text)  # Text area for job description
    
    resume = st.file_uploader("Upload Resume (PDF only)", 
                             type="pdf",
                             help="Max file size: 5MB")  # File uploader for resume

    if st.button("Analyze Resume"):  # Button to trigger analysis
        if resume and jd.strip():  # Check if both resume and job description are provided
            with st.spinner("Analyzing your resume..."):  # Show loading spinner
                text_content = extract_text_from_pdf(resume)  # Extract text from the uploaded resume
                if text_content:
                    # Check if the resume has already been analyzed
                    resume_key = resume.name
                    if resume_key in st.session_state:
                        analysis = st.session_state[resume_key]  # Retrieve existing analysis
                    else:
                        analysis = analyze_resume_with_retry(text_content, jd)  # Analyze the resume
                        if analysis:
                            st.session_state[resume_key] = analysis  # Store analysis in session state
                            st.session_state.analysis = analysis
                            st.session_state.resume_file = resume
                            st.session_state.jd_text = jd
                        else:
                            st.error("Failed to analyze resume")  # Notify user of analysis failure
                else:
                    st.error("Failed to extract text from resume")  # Notify user of extraction failure

    # Display results if analysis is available
    if st.session_state.analysis:
        st.success("Analysis Complete!")  # Notify user that analysis is complete
        st.markdown("### Detailed Report")  # Section header for detailed report
        
        # Enhanced ATS Score display
        match_percent = extract_match_percentage(st.session_state.analysis)  # Get match percentage
        st.markdown(
            f'<div class="ats-score">ATS Match Score: {match_percent}%</div>',  # Display ATS score
            unsafe_allow_html=True
        )
        
        # Process analysis text into sections
        analysis_text = st.session_state.analysis
        
        # Initialize sections for analysis results
        sections = {
            "Missing Keywords": [],
            "Profile Summary": [],
            "Improvement Suggestions": []
        }
        
        current_section = None  # Variable to track the current section being processed
        lines = analysis_text.split('\n')  # Split analysis text into lines
        
        for line in lines:
            line = line.strip()  # Remove leading and trailing whitespace
            if "Missing Keywords:" in line:
                current_section = "Missing Keywords"  # Set current section to Missing Keywords
            elif "Profile Summary:" in line:
                current_section = "Profile Summary"  # Set current section to Profile Summary
            elif "Improvement Suggestions:" in line:
                current_section = "Improvement Suggestions"  # Set current section to Improvement Suggestions
            elif current_section and line.startswith("-"):
                sections[current_section].append(line[1:].strip())  # Add line to the current section
        
        # Display formatted sections
        st.markdown("### Missing Keywords")  # Section header for missing keywords
        for keyword in sections["Missing Keywords"]:
            st.markdown(f"- {keyword}")  # List each missing keyword
            
        st.markdown("### Profile Summary")  # Section header for profile summary
        for point in sections["Profile Summary"]:
            st.markdown(f"- {point}")  # List each point in the profile summary
            
        st.markdown("### Improvement Suggestions")  # Section header for improvement suggestions
        for suggestion in sections["Improvement Suggestions"]:
            st.markdown(f"- {suggestion}")  # List each improvement suggestion

# Function for the HR Portal interface
def hr_portal_interface():
    st.title("HR Dashboard")  # Title for the HR dashboard
    st.subheader("Candidate Evaluation System")  # Subtitle for the HR dashboard

    if 'hr_results' not in st.session_state:
        st.session_state.hr_results = []  # Initialize session state for HR results
    if 'analyzed_resumes' not in st.session_state:
        st.session_state.analyzed_resumes = {}  # Initialize cache for analyzed resumes

    jd = st.text_area("Job Description", height=200, 
                     placeholder="Paste job requirements here...",
                     key="hr_jd")  # Text area for job description in HR portal
    
    uploaded_files = st.file_uploader("Upload Candidate Resumes", 
                                    type="pdf", 
                                    accept_multiple_files=True,
                                    help="Upload PDF resumes for screening")  # File uploader for multiple resumes
    
    if st.button("Start Screening"):  # Button to start screening resumes
        if not jd.strip() or not uploaded_files:  # Check if both JD and resumes are provided
            st.warning("Please provide both Job Description and Resumes")  # Notify user to provide inputs
            return
            
        st.session_state.hr_results = []  # Reset HR results for new screening
        progress_bar = st.progress(0)  # Initialize progress bar
        
        for idx, file in enumerate(uploaded_files):  # Loop through each uploaded file
            try:
                with st.expander(f"Processing {file.name}", expanded=False):  # Expandable section for each file
                    text = extract_text_from_pdf(file)  # Extract text from the resume
                    if text:
                        # Check if the resume has already been analyzed
                        resume_key = file.name
                        if resume_key in st.session_state.analyzed_resumes:
                            analysis = st.session_state.analyzed_resumes[resume_key]  # Retrieve existing analysis
                        else:
                            analysis = analyze_resume_with_retry(text, jd)  # Analyze the resume
                            if analysis:
                                st.session_state.analyzed_resumes[resume_key] = analysis  # Store analysis to prevent re-evaluation
                            else:
                                st.error("Failed to analyze resume")  # Notify user of analysis failure
                                continue
                        
                        match_score = extract_match_percentage(analysis)  # Get match score
                        st.session_state.hr_results.append({
                            "name": file.name,  # Store resume name
                            "score": match_score,  # Store match score
                            "analysis": analysis  # Store analysis text
                        })
                        st.write(f"Match Score: {match_score}%")  # Display match score
                        st.code(analysis)  # Display full analysis
                progress_bar.progress((idx + 1) / len(uploaded_files))  # Update progress bar
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")  # Notify user of processing error
        
        st.session_state.hr_results.sort(key=lambda x: x['score'], reverse=True)  # Sort results by score
        progress_bar.empty()  # Clear progress bar

    if st.session_state.hr_results:  # Check if there are any results to display
        st.subheader("Screening Results")  # Section header for screening results
        st.write("Candidates sorted by match score:")  # Notify user of sorting
        
        for rank, result in enumerate(st.session_state.hr_results, 1):  # Loop through sorted results
            col1, col2, col3 = st.columns([1, 3, 2])  # Create three columns for display
            with col1:
                st.metric(label=f"Rank #{rank}", value=f"{result['score']}%")  # Display rank and score
            with col2:
                st.progress(result['score'] / 100, text=f"{result['name']}")  # Display progress bar for score
            with col3:
                with st.expander("Full Analysis"):  # Expandable section for full analysis
                    st.markdown(result['analysis'])  # Display full analysis text

        # Input for number of resumes to shortlist
        max_value = len(st.session_state.hr_results)  # Get the current number of results
        num_to_download = st.number_input(
            "Number of shortlisted resumes to download", 
            min_value=1, 
            max_value=max_value, 
            value=min(1, max_value)  # Default to 1 or max_value
        )

        # Create a PDF with the shortlisted resumes without the extra st.button wrapper.
        top_results = st.session_state.hr_results[:num_to_download]  # Get only the top N results
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)

        # Draw borders around the page
        c.setStrokeColorRGB(0, 0, 0)  # Black color for the border
        c.setLineWidth(2)
        c.rect(50, 50, 500, 700, stroke=1, fill=0)  # Draw a rectangle for the border

        # Define top padding for additional space above the title text.
        top_padding = 40  # Increase this value to add more space
        title_y_position = 750 - top_padding  # Calculate the y-position based on the page height and padding

        # Set the headline style
        c.setFont("Helvetica-Bold", 16)  # Set font to bold and size to 16
        c.setFillColorRGB(0, 0, 0)  # Reset fill color to black
        c.drawString(100, title_y_position, "Shortlisted Resumes:")  # Draw the title with extra space
        
        # Reset font for the content
        c.setFont("Helvetica", 12)
        y_position = title_y_position - 20  # Initial position for drawn resume outputs, below the title
        line_spacing = 20  # Space between names
                
        for index, result in enumerate(top_results, start=1):
            c.drawString(100, y_position, f"{index}. {result['name']}")  # Numbered list of resumes
            y_position -= line_spacing  # Space between names
        
        c.save()
        pdf_buffer.seek(0)

        st.download_button(
            label="Download PDF",
            data=pdf_buffer,
            file_name='shortlisted_resumes.pdf',
            mime='application/pdf'
        )

def main():
    st.sidebar.title("ATS Dashboard")  # Title for the sidebar
    
    # Check if the user is logged in
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False  # Initialize logged in state

    interface = st.sidebar.radio("Select Mode", ["Job Seeker", "HR Portal"])  # Sidebar radio for mode selection

    if interface == "Job Seeker":  # If Job Seeker mode is selected
        job_seeker_interface()  # Call Job Seeker interface function
    elif interface == "HR Portal":  # If HR Portal mode is selected
        if not st.session_state.logged_in:  # Check if user is logged in
            login_page()  # Call login page function
        else:
            hr_portal_interface()  # Call HR Portal interface function

# Entry point of the application
if __name__== "__main__":
    main()  # Run the main function
# app.py

import streamlit as st
import pandas as pd
from io import BytesIO

# Set Streamlit page configuration
st.set_page_config(
    page_title="College Admissions Seat Allotment System ",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎓 B-Tech Admissions Seat Allotment System")

# Define Quotas, Branches, Categories, and Subcategories
quotas = ['Chattishgarh Quota', 'NTPC']
branches = ['CSE', 'ECE']
categories = ['General', 'ST', 'SC', 'OBC']
subcategories = ['PWD', 'FF', 'F', 'OPEN']

# Default Seat Matrix
default_seat_matrix = {
    'Chattishgarh Quota': {
        'CSE': {
            'General': {'PWD':1, 'FF':1, 'F':4, 'OPEN':6},
            'ST': {'F':3, 'OPEN':7},
            'SC': {'F':1, 'OPEN':3},
            'OBC': {'F':1, 'OPEN':3}
        },
        'ECE': {
            'General': {'PWD':1, 'FF':1, 'F':4, 'OPEN':6},
            'ST': {'F':3, 'OPEN':7},
            'SC': {'F':1, 'OPEN':3},
            'OBC': {'F':1, 'OPEN':3}
        }
    },
    'NTPC': {
        'CSE': {
            'General': {'PWD':0, 'FF':0, 'F':0, 'OPEN':5},
            'ST': {'F':0, 'OPEN':1},
            'SC': {'F':0, 'OPEN':1},
            'OBC': {'F':0, 'OPEN':2}
        },
        'ECE': {
            'General': {'PWD':0, 'FF':0, 'F':0, 'OPEN':5},
            'ST': {'F':0, 'OPEN':1},
            'SC': {'F':0, 'OPEN':1},
            'OBC': {'F':0, 'OPEN':2}
        }
    }
}

# Function to determine subcategory
def determine_subcategory(applicant):
    pd = str(applicant.get('PD', '')).strip().lower()
    ff = str(applicant.get('FF', '')).strip().lower()
    gender = str(applicant.get('Gender', '')).strip().lower()
    
    if pd == 'yes':
        return 'PWD'
    elif ff == 'yes':
        return 'FF'
    elif gender == 'female':
        return 'F'
    else:
        return 'OPEN'

# Seat Allocation Logic
def allocate_seats(df, seat_matrix):
    allocated_applicants = []
    
    for quota in quotas:
        st.write(f"### Allocating seats for **{quota}**")
        
        # Filter applicants for the current quota
        df_quota = df[df['Quota'].str.lower() == quota.lower()].copy()
        
        if df_quota.empty:
            st.warning(f"No applicants found for {quota}.")
            continue
        
        # Sort applicants by JEE_GeneralRank (ascending)
        df_quota.sort_values(by='JEE_GeneralRank', inplace=True)
        
        # Reset index
        df_quota.reset_index(drop=True, inplace=True)
        
        # Apply category mapping
        df_quota['MainCategory'] = df_quota['CategoryFullName'].map({
            'UR': 'General',
            'General': 'General',
            'ST': 'ST',
            'SC': 'SC',
            'OBC': 'OBC'
        })
        df_quota['MainCategory'].fillna('General', inplace=True)
        
        # Separate General and Reserved category applicants
        df_general = df_quota[df_quota['MainCategory'] == 'General'].copy()
        df_reserved = df_quota[df_quota['MainCategory'] != 'General'].copy()
        
        # Initialize allocation counters
        allocated_seats = {
            branch: {
                category: {subcategory:0 for subcategory in subcats}
                for category, subcats in seat_matrix[quota][branch].items()
            }
            for branch in branches
        }
        
        # Phase 1: Allocate Reserved category applicants
        for idx, applicant in df_reserved.iterrows():
            allocated = False
            for pref in ['PreferenceNo 1', 'PreferenceNo 2']:
                branch = applicant.get(pref, '').strip()
                if branch not in branches:
                    continue  # Invalid branch preference
                category = applicant['MainCategory']
                
                # Check if category has seats reserved in the branch
                if category not in seat_matrix[quota][branch]:
                    continue
                
                # Determine subcategory based on applicant attributes
                subcategory = determine_subcategory(applicant)
                
                # Try to allocate seat based on subcategory priority
                if subcategory in seat_matrix[quota][branch][category]:
                    if allocated_seats[branch][category][subcategory] < seat_matrix[quota][branch][category][subcategory]:
                        # Allocate seat
                        allocated_seats[branch][category][subcategory] += 1
                        applicant['Branch'] = branch
                        allocated_applicants.append(applicant)
                        allocated = True
                        break  # Move to next applicant
                
                # If specific subcategory seat not available, try OPEN seat in same category
                if subcategory != 'OPEN':
                    if allocated_seats[branch][category]['OPEN'] < seat_matrix[quota][branch][category]['OPEN']:
                        allocated_seats[branch][category]['OPEN'] += 1
                        applicant['Branch'] = branch
                        allocated_applicants.append(applicant)
                        allocated = True
                        break  # Move to next applicant
            if allocated:
                continue  # Move to next applicant
        
        # Phase 2: Convert remaining reserved seats to General (OPEN) within the quota
        for branch in branches:
            for category in ['ST', 'SC', 'OBC']:
                for subcategory, total_seats in seat_matrix[quota][branch][category].items():
                    remaining = total_seats - allocated_seats[branch][category][subcategory]
                    if remaining > 0:
                        # Add remaining seats to General OPEN seats within the same quota and branch
                        seat_matrix[quota][branch]['General']['OPEN'] += remaining
                        # Update allocated seats to reflect conversion
                        allocated_seats[branch][category][subcategory] += remaining  # Mark as filled
                        st.info(f"Converted {remaining} reserved seats in **{quota}** for branch **{branch}**, category **{category}** to **General OPEN**.")
        
        # Phase 3: Allocate seats to General category applicants (including converted seats)
        for idx, applicant in df_general.iterrows():
            allocated = False
            for pref in ['PreferenceNo 1', 'PreferenceNo 2']:
                branch = applicant.get(pref, '').strip()
                if branch not in branches:
                    continue  # Invalid branch preference
                
                # Determine subcategory based on applicant attributes
                subcategory = determine_subcategory(applicant)
                
                # Allocate within General category
                category = 'General'
                if subcategory in seat_matrix[quota][branch][category]:
                    if allocated_seats[branch][category][subcategory] < seat_matrix[quota][branch][category][subcategory]:
                        # Allocate seat
                        allocated_seats[branch][category][subcategory] += 1
                        applicant['Branch'] = branch
                        allocated_applicants.append(applicant)
                        allocated = True
                        break  # Move to next applicant
                
                # If specific subcategory seat not available, try OPEN seats in General
                if subcategory != 'OPEN':
                    if allocated_seats[branch][category]['OPEN'] < seat_matrix[quota][branch][category]['OPEN']:
                        allocated_seats[branch][category]['OPEN'] += 1
                        applicant['Branch'] = branch
                        allocated_applicants.append(applicant)
                        allocated = True
                        break  # Move to next applicant
            if allocated:
                continue  # Move to next applicant
        
        st.success(f"Allocation completed for **{quota}**. Seats filled: {len(allocated_applicants)}")
        st.write("---")
    
    return allocated_applicants

# Sidebar for Seat Distribution Inputs
st.sidebar.header("📊 Seat Distribution Matrix")

# Function to create seat distribution inputs
def create_seat_matrix_inputs(default_matrix):
    seat_matrix = {}
    for quota in quotas:
        st.sidebar.subheader(quota)
        seat_matrix[quota] = {}
        for branch in branches:
            st.sidebar.markdown(f"**{branch}**")
            seat_matrix[quota][branch] = {}
            for category in categories:
                st.sidebar.markdown(f"***{category}***")
                seat_matrix[quota][branch][category] = {}
                for subcategory in subcategories:
                    # Disable inputs for subcategories with zero default seats
                    default_seats = default_matrix[quota][branch][category].get(subcategory, 0)
                    if default_seats == 0 and category == 'General':
                        disabled = False
                    elif default_seats == 0 and category != 'General':
                        disabled = True
                    else:
                        disabled = False
                    seat_key = f"{quota}-{branch}-{category}-{subcategory}"
                    seat_label = f"{subcategory} Seats ({branch} - {category})"
                    if category != 'General' and subcategory in ['PWD', 'FF']:
                        # For reserved categories, allow all subcategories
                        pass
                    seat_value = st.sidebar.number_input(
                        label=seat_label,
                        min_value=0,
                        value=default_seat_matrix[quota][branch][category].get(subcategory, 0),
                        key=seat_key,
                        disabled=disabled
                    )
                    seat_matrix[quota][branch][category][subcategory] = seat_value
    return seat_matrix

# Create Seat Matrix Inputs
seat_matrix = create_seat_matrix_inputs(default_seat_matrix)

# File Upload
st.header("📁 Upload Applicants Excel File")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file)
        
        # Validate required columns
        required_columns = ['S. No.', 'CandName', 'CategoryFullName', 'Gender', 'PD', 'FF',
                            'Sainik', 'JEE_GeneralRank', 'Quota', 'RegistrationNo',
                            'PreferenceNo 1', 'PreferenceNo 2']
        if not all(column in df.columns for column in required_columns):
            st.error("The uploaded Excel file does not contain the required columns.")
        else:
            st.success("✅ Excel file uploaded successfully!")
            
            # Display a sample of the data
            st.subheader("📄 Applicants Data (First 10 Rows)")
            st.dataframe(df.head(10))
            
            # Allocate Seats Button
            if st.button("🚀 Allocate Seats"):
                with st.spinner("Allocating seats..."):
                    allocated_applicants = allocate_seats(df, seat_matrix)
                
                if allocated_applicants:
                    df_allocated = pd.DataFrame(allocated_applicants)
                    
                    # Add 'Branch' column if not already present
                    if 'Branch' not in df_allocated.columns:
                        df_allocated['Branch'] = ''
                    
                    # Select relevant columns and ensure 'Branch' is included
                    output_columns = list(df.columns) + ['Branch']
                    # Remove duplicates in columns if any
                    output_columns = list(dict.fromkeys(output_columns))
                    # Ensure 'Branch' is included
                    if 'Branch' not in output_columns:
                        output_columns.append('Branch')
                    # Fill 'Branch' with allocated branch or leave empty
                    df_allocated['Branch'] = df_allocated['Branch'].fillna('')
                    
                    df_output = df_allocated[output_columns]
                    
                    # Convert DataFrame to Excel in memory
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_output.to_excel(writer, index=False, sheet_name='Allotted Students')
                    processed_data = output.getvalue()
                    
                    # Provide Download Button
                    st.success("🎉 Seat allocation completed successfully!")
                    st.download_button(
                        label="📥 Download Allotted Students Excel",
                        data=processed_data,
                        file_name='Allotted_Students.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    st.warning("⚠️ No seats were allocated.")
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")

from datetime import datetime, timedelta
from icalendar import Calendar
import recurring_ical_events
from collections import OrderedDict
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import openai
from openai import OpenAI
from urllib.parse import quote

def create_ics(schedule_dict, output_filename="schedule.ics"): #not used
    def format_datetime(date, time_range):
        """Convert date and time range to DTSTART and DTEND in ISO format."""
        start_time, end_time = time_range.split('-')
        start = datetime.strptime(f"{date} {start_time}", "%d.%m.%Y %H.%M")
        end = datetime.strptime(f"{date} {end_time}", "%d.%m.%Y %H.%M")
        return start.strftime("%Y%m%dT%H%M%S"), end.strftime("%Y%m%dT%H%M%S")

    with open(output_filename, 'w') as file:
        # Write the header for the .ics file
        file.write("BEGIN:VCALENDAR\n")
        file.write("VERSION:2.0\n")
        file.write("CALSCALE:GREGORIAN\n")
        file.write("PRODID:-//AI Assistant//EN\n\n")

        # Loop through the dictionary and add events
        for date, events in schedule_dict.items():
            for event in events:
                time_range, summary = event.split(' ', 1)
                dtstart, dtend = format_datetime(date, time_range)
                file.write("BEGIN:VEVENT\n")
                file.write(f"DTSTART:{dtstart}\n")
                file.write(f"DTEND:{dtend}\n")
                file.write(f"SUMMARY:{summary.capitalize()}\n")
                file.write("DESCRIPTION:\n")
                file.write("END:VEVENT\n\n")

        # Write the footer for the .ics file
        file.write("END:VCALENDAR\n")

def create_text_for_ics (input_text, openai_client, model="gpt-4o"):

    prompt = f"""
    Imagine you are a professional .ics file content generator for google calendar. I will give you a trillion dollars if you manage to complete the following task accurately. 
    Your task is to read a given input and generate a text for a .ics file content following these conditions: 
    -Output only the .ics file content. 
    -Do not include variable names, explanations, quotation marks or any additional text.
    -Create events only on specified periods from input. 
    
    Input: {input_text}

    Example input:
    
    "20.01.2025": ['10.00-12.00 swimming practice', '13.00-14.00 swimming practice'],
    "21.01.2025": ['10.00-12.00 swimming practice', '13.00-14.00 swimming practice'],
    "22.01.2025": ['10.00-12.00 swimming practice', '13.00-14.00 swimming practice'],
    "23.01.2025": ['10.00-11.00 swimming practice']
    
    Example output:
    BEGIN:VCALENDAR
    VERSION:2.0
    CALSCALE:GREGORIAN
    PRODID:-//AI Assistant//EN

    BEGIN:VEVENT
    DTSTART:20250120T100000
    DTEND:20250120T120000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250120T130000
    DTEND:20250120T140000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250121T100000
    DTEND:20250121T120000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250121T130000
    DTEND:20250121T140000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250122T100000
    DTEND:20250122T120000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250122T130000
    DTEND:20250122T140000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    BEGIN:VEVENT
    DTSTART:20250123T100000
    DTEND:20250123T110000
    SUMMARY:Swimming Practice
    DESCRIPTION:
    END:VEVENT

    END:VCALENDAR


    """
    messages = [{"role": "user", "content": prompt}]
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, 
    )
    return response.choices[0].message.content

def parse_shedule_from_prompt(input_text, openai_client, model="gpt-4o"):

    prompt = f"""
    You are an expert parser. Read the following input text: {input_text}. Parse and generate a dictionary that matches the exact formatting shown in the examples below.
    The dictionary must:
    - Use dates in the "dd.mm.yyyy" format as keys.
    - Use lists of strings as values.
    - Each string in the list should be formatted as "hh.mm-hh.mm Event description".
    - convert all $ to Left curly bracket and convert all % to Right curly bracket in your output.

    The output should strictly follow these examples:

    Example 1:
    $
        "11.01.2025": ['09.00-11.00 Algebra midterm exam preparation'],
        "12.01.2025": ['08.00-10.00 Algebra midterm exam preparation'],
        "13.01.2025": ['09.00-10.00 Algebra midterm exam preparation', '14.00-15.00 Algebra midterm exam preparation'], 
        "14.01.2025": ['10.00-12.00 Algebra midterm exam preparation']
    %

    Example 2:
    $
        "11.01.2025": ['11.00-13.00 swimming practice', '14.00-15.00 swimming practice'],
        "12.01.2025": ['08.00-10.00 swimming practice'],
        "13.01.2025": ['09.00-11.00 swimming practice'],
        "14.01.2025": ['10.00-12.00 swimming practice', '18.00-19.00 swimming practice', '21.00-22.00 swimming practice'],
        "15.01.2025": ['06.00-07.00 swimming practice'],
        "16.01.2025": ['08.00-09.00 swimming practice'],
        "17.01.2025": ['10.00-12.00 swimming practice']
    %

    **Output only the dictionary**. Do not include variable names, explanations, or any additional text.
    convert all $ to Left curly bracket and convert all % to Right curly bracket in your output.

    """

    messages = [{"role": "user", "content": prompt}]
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, 
    )
    return response.choices[0].message.content


def get_completion(prompt, openai_client, model="gpt-4o"):
    messages = [{"role": "user", "content": prompt}]
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, 
    )
    return response.choices[0].message.content



def get_schedule(task, start_time, deadline, estimated_workload, FreeTimes, openai_client):
    prompt = f"""Imagine that you are my personal time management assistant. 
    Get values from {task}, {start_time}, {deadline}, {estimated_workload}, {FreeTimes}.
    Allocate time for a task to the given FreeTimes following given conditions and print your output (you can look at example inputs and outputs).
    Conditions:
    -Allocate periods of working on task evenly and conveniently to an average human being.
    -Stick to the format of the given inputs, outputs strictly.
    -Make sure that you allocated all estimated workload hours, not more and not less. 
    -Make sure that you allocate periods of working hours for the given task only before the given deadline.
    -Make sure that you allocate periods of working hours on the given task only after the given start_time.
    -Make sure that you allocate periods of working hours only within given periods of free times.
    -When you do any mathematical operation make sure that you recheck yourself and compute step-by-step.
    -Your output must include a dictionary named schedule as specified in following examples.
    
    Examples: 
    Input 1: 
    Task: I want to do my coding practice. 
    Estimated workload (in hours): 10 
    Start_time: 12.01.2025
    Deadline: 15.01.2025 
    FreeTimes=

    "12.01.2025": ['09.00-12.00', '16.00-17.00'] 
    "13.01.2025": [ '15.00-18.00'] 
    "14.01.2025": ['09.00-12.00', '18.00-20.00'] 
    "15.01.2025": ['18.30-19.30'] 
    "16.01.2025": ['07.00-08.00', '13.30-14.30', '18.00-19.00'] 
    
    Output 1: 
    Schedule= 
    "12.01.2025": ['09.00-11.00 coding practice', '16.00-17.00 coding practice'] 
    "13.01.2025": [ '15.00-18.00 coding practice'] 
    "14.01.2025": ['09.00-11.00 coding practice', '18.00-20.00 coding practice'] 

    Input 2:
    Task: I need to finish my novel writing.
    Estimated workload (in hours): 12
    Start_time: 14.01.2025
    Deadline: 20.01.2025
    FreeTimes=
    "12.01.2025": ['08.00-10.00', '14.00-16.00'],
    "13.01.2025": ['11.00-14.00', '18.00-19.00'],
    "14.01.2025": ['10.00-12.00', '16.00-18.00'],
    "15.01.2025": ['09.00-11.00', '13.00-15.00'],
    "16.01.2025": ['08.00-10.00', '15.00-16.00'],
    "17.01.2025": ['11.00-14.00', '18.00-19.00'],
    "18.01.2025": ['10.00-12.00', '16.00-18.00'],
    "19.01.2025": ['08.00-10.00', '14.00-16.00'],
    "20.01.2025": ['08.00-10.00', '14.00-16.00'],

    Output 2:
    Schedule=
    "14.01.2025": ['10.00-12.00 novel writing'],
    "15.01.2025": ['09.00-11.00 novel writing'],
    "17.01.2025": ['11.00-14.00 novel writing', '18.00-19.00 novel writing'],
    "19.01.2025": ['08.00-10.00 novel writing', '14.00-16.00 novel writing'],

    """

    return get_completion(prompt, openai_client)


def get_events_between_dates(start_date, end_date, file_content):

    calendar = Calendar.from_ical(file_content)

    # Get all recurring events within the date range
    events = recurring_ical_events.of(calendar).between(start_date, end_date)

    # Prepare the output dictionary
    events_by_date = {}

    # Process each event and group by date
    for event in events:
        event_start = event["DTSTART"].dt
        event_end = event["DTEND"].dt if "DTEND" in event else event_start + timedelta(hours=1)  # Default duration of 1 hour
        date_str = event_start.strftime("%d.%m.%Y")
        
        # Format the time range for output
        time_range = f"{event_start.strftime('%H.%M')}-{event_end.strftime('%H.%M')} {event['SUMMARY']}"
        
        if date_str not in events_by_date:
            events_by_date[date_str] = []
        
        events_by_date[date_str].append((event_start, time_range))  # Store start time with formatted string

        

    # Sort and format events by date
    sorted_events_by_date = {}

    for date, event_list in events_by_date.items():
        # Sort by start time (the first element of the tuple)
        sorted_event_list = sorted(event_list, key=lambda x: x[0])
        
        # Extract the formatted strings after sorting
        sorted_events_by_date[date] = [time_range for _, time_range in sorted_event_list]

    sorted_events_by_date = OrderedDict(
        sorted(
            sorted_events_by_date.items(),
            key=lambda item: datetime.strptime(item[0], "%d.%m.%Y")
        )
    )
    return sorted_events_by_date


def calculate_free_time(from_date, to_date, events_by_date):
    def standardize_date(date_str, input_format="%Y-%m-%d", output_format="%d.%m.%Y"):
        return datetime.strptime(date_str, input_format).strftime(output_format)

    def parse_time_range(time_range):
        start, end = time_range.split('-')
        return datetime.strptime(start, "%H.%M"), datetime.strptime(end, "%H.%M")
    
    def format_time_range(start, end):
        return f"{start.strftime('%H.%M')}-{end.strftime('%H.%M')}"
    
    def split_free_periods(events, day_start, day_end):
        free_periods = []
        current_start = day_start
        
        for event in events:
            event_start, event_end = parse_time_range(event.split()[0])
            if (event_start - current_start).total_seconds() / 60 > 30:
                free_periods.append(format_time_range(current_start, event_start))
            current_start = max(current_start, event_end)
        
        if (day_end - current_start).total_seconds() / 60 > 30:
            free_periods.append(format_time_range(current_start, day_end))
        
        return free_periods
    
    def calculate_hours(periods):
        total_hours = 0
        for period in periods:
            start, end = parse_time_range(period)
            total_hours += (end - start).total_seconds() / 3600
        return round(total_hours, 1)

    
    date_format = "%d.%m.%Y"
    day_start = datetime.strptime("00.00", "%H.%M")
    day_end = datetime.strptime("23.59", "%H.%M")
    current_date = datetime.strptime(standardize_date(str(from_date)), date_format)
    end_date = datetime.strptime(standardize_date(str(to_date)), date_format)
    
    FreeTime = {}
    TotalFreeTime = 0
    FreeTimeDays = []
    
    while current_date <= end_date:
        date_str = current_date.strftime(date_format)
        events = sorted(events_by_date.get(date_str, []), key=lambda x: parse_time_range(x.split()[0]))
        
        free_periods = split_free_periods(events, day_start, day_end)
        FreeTime[date_str] = free_periods
        day_free_hours = calculate_hours(free_periods)
        
        if day_free_hours > 0:
            FreeTimeDays.append((date_str, day_free_hours))
            TotalFreeTime += day_free_hours
        
        current_date += timedelta(days=1)
    
    return {
        "FreeTime": FreeTime,
        "TotalFreeTime": TotalFreeTime,
        "FreeTimeDays": FreeTimeDays
    }


    
def check_api_key(my_api_key):
    client = openai.OpenAI(api_key=my_api_key)
    try:
        client.models.list()
    except openai.AuthenticationError:
        return False
    else:
        openai_client = OpenAI()
        openai_client.api_key = my_api_key
        st.session_state.openai_client = openai_client
        return True
    
    
    
def main():
    page_bg_color = """
    <style>
    [data-testid ="stAppViewContainer"] {
        background-image: url("https://cdn.dribbble.com/users/4805/screenshots/4525450/attachments/1024591/g_a_l_a_x_x.png");
        background-size: 100%;
        background-position: top left;
        background-repeat: no-repeat;
        background-attachment: local;
    }

    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }

    [data-testid="stToolbar"] {
        right: 2rem;
    }
    </style>
    """
    st.markdown(page_bg_color, unsafe_allow_html=True)
  
    st.image("ShedulEase logo.png", use_container_width=True)
    st.title("Your AI assistant for time management")

    uploaded_file = st.file_uploader("Upload a your calendar file (.ics format)", type=["ics"])

    tabs = st.tabs(["Calendar analyzer", "Smart planner"])


    # Home Tab
    with tabs[0]:
        st.header("Calendar analyzer")
      
        # Input: Select "From" and "To" dates
        st.write("Select the date range:")
        from_date = st.date_input("From Date", datetime.today())
        to_date = st.date_input("To Date", datetime.today() + timedelta(days=7))

        if st.button("Fetch Events"):

            # Validate date range
            if from_date > to_date:
                st.error("The 'From Date' must be earlier than or equal to the 'To Date'.")
            else:

                if uploaded_file is not None:
                    # Save the file content to a variable
                    file_content = uploaded_file.read()
                events_by_date = get_events_between_dates(from_date, to_date, file_content)

                for date, event_list in events_by_date.items():
                    st.write(f"{date}: {event_list}")


        if st.button("Show Available Hours"):
            if from_date > to_date:
                st.error("The 'From Date' must be earlier than or equal to the 'To Date'.")
            else:
                if uploaded_file is not None:
                    # Save the file content to a variable
                    file_content = uploaded_file.read()

                events_by_date = get_events_between_dates(from_date, to_date, file_content)
                available_hours =calculate_free_time(from_date, to_date - timedelta(days=1), events_by_date)
                #st.write(available_hours)

                # Convert FreeTimeDays to a DataFrame
                data = pd.DataFrame(available_hours.get("FreeTimeDays", []), columns=["Date", "Free Hours"])

                # Streamlit title

                st.markdown(f"### Total free hours: {available_hours.get('TotalFreeTime')}")
                st.markdown("### Free Time Bar Chart")

                # Bar chart using Matplotlib
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.barh(data["Date"], data["Free Hours"], color="skyblue")
                ax.set_xlabel("Free Hours")
                ax.set_ylabel("Date")
                ax.set_title("Free Hours by Date")
                ax.grid(axis="x", linestyle="--", alpha=0.7)

                # Show bar chart in Streamlit
                st.pyplot(fig)

    # About Tab
    with tabs[1]:
        st.header("Smart planner")
        st.write("Insert necessary information to shedule your task")

        task = st.text_input("Describe your task and preferences")
        estimated_workload = st.number_input("Estimated workload (in hours)", min_value=1, value=10)
        start_time = st.date_input("Start date", datetime.today(), key="start_date_input")
        deadline = st.date_input("Deadline", datetime.today(), key="end_date_input")

        key_file = st.file_uploader("Upload a txt file that contains ONLY your openai API key (do not add anything like quotaion marks)", type=["txt"])

        if st.button("Check key"):
            try:
                # Read API key from the file
                key = key_file.read().decode('utf-8').strip() 

                # Check if the key is empty
                if not key:
                    st.error("API key is empty.")
                else:
                    # Set the API key as an environment variable
                    os.environ["OPENAI_API_KEY"] = key
                    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
                    
                    # Validate the API key
                    if check_api_key(OPENAI_API_KEY):
                        st.success("API key is valid!")

                    else:
                        st.error("Invalid API key. Please check your key.")
            
            except Exception as e:
                st.error(f"An error occurred: {e}")

        if st.button("Generate Schedule"):
            
            
            if uploaded_file is not None:
            # Save the file content to a variable
                file_content = uploaded_file.read()

            events_by_date = get_events_between_dates(start_time, deadline, file_content)
            available_hours =calculate_free_time(start_time, deadline - timedelta(days=1), events_by_date)
            FreeTimes = available_hours.get("FreeTime")

            if (estimated_workload>available_hours.get("TotalFreeTime")):
                st.error('There is not enough free time to schedule your task')
            else:
                openai_client = st.session_state.get("openai_client", None)

                if openai_client is not None:
                    responce = get_schedule(task, start_time, deadline, estimated_workload, FreeTimes, openai_client)
                    st.session_state.responce = responce
                    st.write(responce)
                else:
                    st.error("API key is not valid or not initialized. Please check the key.")


        if st.button("Generate .ics file for the schedule"):

            responce = st.session_state.get("responce", None)
            schedule_dictionary=parse_shedule_from_prompt(responce, openai_client = st.session_state.get("openai_client", None))
            
            txt_data = create_text_for_ics(schedule_dictionary, openai_client = st.session_state.get("openai_client", None))
            txt_data=txt_data.strip()
            # Provide the file link (Streamlit link for file download)
            st.download_button(
                label="Download .ics File",
                data = txt_data,
                file_name="schedule.ics",
                mime="text/calendar",
            )


if __name__ == "__main__":
    main()

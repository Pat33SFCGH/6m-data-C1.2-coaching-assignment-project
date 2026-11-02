import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# Sets the page configuration
# You can set the page title and layout here
st.set_page_config(page_title="Singapore Jobs Analytics Dashboard", layout="wide")
st.title("Singapore Jobs Analytics Dashboard")

# 1. Define a function to load the data and add the cache decorator
@st.cache_data
def load_data(path):
    return pd.read_csv(path, nrows=5000)

# Kindly change to the corect csv file path
DATA_PATH = "/home/patss/DSAIModule_GA1/6m-data-C1.2-coaching-assignment-project/SJA/data/SGJobData.csv"
df = load_data(DATA_PATH)

st.header("Key Metrics")
# Create four columns for the metrics and unpack them
# We can then use each column to place a metric
filtered_df = df.copy()
col1, col2, col3, col4 = st.columns(4)
#col1
try:
    # Get the raw string from the most common category row
    raw_json_str = filtered_df["categories"].value_counts().index[0]
    
    # Clean up any potential double-escaped quotes and parse the JSON list
    cleaned_str = raw_json_str.replace('""', '"')
    category_list = json.loads(cleaned_str)
    
    # Extract the string "Information Technology"
    top_category = category_list[0]["category"]
except (IndexError, json.JSONDecodeError, KeyError):
    top_category = "No Data"
col1.metric("Top Category", top_category)
col2.metric("Top Position", filtered_df["positionLevels"].value_counts().index[0])
col3.metric("Total Available Job Application", f"{filtered_df[filtered_df['status_jobStatus'].isin(['Open', 'Re-open'])]['metadata_totalNumberJobApplication'].sum():,.0f}")
col4.metric("Average Min. Salary - Max. Salary / Average Salary", f"${filtered_df['salary_minimum'].mean():,.0f} - ${filtered_df['salary_maximum'].mean():,.0f} / ${filtered_df['average_salary'].mean():,.0f}")

st.header("Singapore Jobs Analytics Overview")
# 2. Create the Pie Chart using Plotly Express
# Replace 'category_column' and 'value_column' with your actual CSV headers
# --- FIX DOUBLED QUOTES AND EXTRACT CATEGORIES ---
def parse_malformed_json(val):
    if pd.isna(val):
        return []
    try:
        # Convert to string and sanitize doubled double quotes ("" -> ")
        clean_str = str(val).strip()

        # Strip outer quotes if they exist from the CSV interpretation
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]

        # Replace doubled double quotes with single double quotes
        clean_str = clean_str.replace('""', '"')

        # Parse into a valid Python list of dictionaries
        parsed_list = json.loads(clean_str)

        # Extract only the textual 'category' strings
        return [
            item["category"] for item in parsed_list if "category" in item
        ]
    except Exception:
        return []

st.subheader("Category Breakdown (Grouped)")
if "categories" in df.columns:
    # Extract the nested items out into lists
    df["clean_list"] = df["categories"].apply(parse_malformed_json)
    # Explode the lists so each category gets its own independent row row
    exploded_df = df.explode("clean_list").dropna(subset=["clean_list"])

    # --- COUNT AND AGGREGATE ---
    category_counts = (
        exploded_df["clean_list"].value_counts().reset_index()
    )
    category_counts.columns = ["category", "count"]

    # Filter out tiny values < 1% to get rid of the overlapping gray lines in your chart
    total_count = category_counts["count"].sum()
    threshold = total_count * 0.01

    main_categories = category_counts[category_counts["count"] >= threshold]
    other_categories = category_counts[category_counts["count"] < threshold]

    if not other_categories.empty:
        others_row = pd.DataFrame(
            [{"category": "Others", "count": other_categories["count"].sum()}]
        )
        category_counts = pd.concat(
            [main_categories, others_row], ignore_index=True
        )
    else:
        category_counts = main_categories

    # --- RENDER NEW PIE CHART ---
    fig_pie_category = px.pie(
        category_counts,
        names="category",  # Legend will strictly display cleanly now!
        values="count",
        #title="Category Breakdown (Grouped)",
    )

    st.plotly_chart(fig_pie_category, use_container_width=True)
else:
    st.error("Could not find the 'categories' column.")

# Bar Chart for Position by Category
#--- 1. BUILD THE BAR CHART ---
st.subheader("Position for Top 10 Category")
# --- 1. CLEAN THE JSON CATEGORIES ---
def extract_category_name(json_str):
    try:
        # Fix any double-escaped quotes and parse the JSON string
        cleaned_str = str(json_str).replace('""', '"')
        data = json.loads(cleaned_str)

        # Safely extract the string from the 'category' key
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("category", "Unknown")
        elif isinstance(data, dict):
            return data.get("category", "Unknown")
    except Exception:
        return "Unknown"

    return "Unknown"

# Create a temporary column with clean, plain-text category names
df_clean = filtered_df.copy()
df_clean["clean_category"] = df_clean["categories"].apply(
    extract_category_name
)

# --- 2. AGGREGATE THE DATA ---
# Group by the clean text names and count occurrences
count_position_by_category = (
    df_clean.groupby(["positionLevels", "clean_category"])
    .size()
    .reset_index(name="count")
)

# --- 2.5: CALCULATE TRUE TOTALS PER CATEGORY AND FIND TOP 10 ---
category_totals = (
    count_position_by_category.groupby("clean_category")["count"]
    .sum()
    .sort_values(ascending=False)
)
top_10_categories = category_totals.head(10).index.tolist()

# Filter your main summary table to include ONLY those top 10 categories
count_position_by_category = count_position_by_category[
    count_position_by_category["clean_category"].isin(
        top_10_categories
    )
]

# --- 3. BUILD AND DISPLAY THE PLOTLY BAR CHART ---
fig_category_position = px.bar(
    count_position_by_category,
    x="clean_category",
    y="count",
    color="positionLevels",  # Colors bars by position level (e.g., Senior Management)
    barmode="group",
    labels={"clean_category": "Category", "count": "Number of Positions", "positionLevels": "Position Level"},
)

# --- 3.5: FORCE PLOTLY TO RESPECT THE TOTALS SORT ORDER ---
fig_category_position.update_layout(
    xaxis={
        "categoryorder": "array",
        "categoryarray": top_10_categories,  # Enforces biggest total category on the far left
    }
)

# Render the clean chart
st.plotly_chart(fig_category_position, use_container_width=True)

# Bar Chart for Experience by Role Position
#--- 1. BUILD THE BAR CHART ---
st.subheader("Minimum Working Experience by Position")

# --- 2. AGGREGATE THE DATA ---
# Group by the clean text names and count occurrences
count_minexperience_by_position = (
    df_clean.groupby(["minimumYearsExperience", "positionLevels"])
    .size()
    .reset_index(name="count")
)

# CRITICAL FIX: Convert years of experience to string text
# This forces Plotly to treat experience as distinct groups rather than a continuous gradient
count_minexperience_by_position["minimumYearsExperience"] = (
    count_minexperience_by_position["minimumYearsExperience"]
    .astype(int)
    .astype(str)
    + " Years"
)

position_totals = (
    count_minexperience_by_position.groupby("positionLevels")["count"]
    .sum()
    .sort_values(ascending=False)
)
sorted_positions = position_totals.index.tolist()

# --- 3. BUILD AND DISPLAY THE PLOTLY BAR CHART ---
fig_position_experience = px.bar(
    count_minexperience_by_position,
    x="positionLevels",
    y="count",
    color="minimumYearsExperience",  # Colors bars by minimum years of experience
    barmode="group",
    labels={"positionLevels": "Position", "count": "Number of Position", "minimumYearsExperience": "Years of Minimum Experience"},
)

# --- 3.5: Enforce the total-based sorting order onto the X-axis ---
fig_position_experience.update_layout(
    xaxis={
        "categoryorder": "array", 
        "categoryarray": sorted_positions
    }
)

# Render the clean chart
st.plotly_chart(fig_position_experience , use_container_width=True)
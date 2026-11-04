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
DATA_PATH = "./SGJobData.csv"
df = load_data(DATA_PATH)

# Added on 4-Nov-2026
# =====================================================================
# 1. DEFINE UTILITY FUNCTIONS AT THE VERY TOP
# =====================================================================
def format_category_row_unified(val):
    # Reuse your existing robust parser to get the clean list of strings
    names = parse_malformed_json(val)
    # Join them with a comma so they form a single option string
    return ", ".join(names) if names else None

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
# Ended on 4-Nov-2026

# Added on 4-Nov-2026
# Side Bar - Start
st.sidebar.header("Filtering Criteria")

df["metadata_newPostingDate"] = pd.to_datetime(df["metadata_newPostingDate"])
postingdate_min = df["metadata_newPostingDate"].min().date()
postingdate_max = df["metadata_newPostingDate"].max().date()
postingdate_range = st.sidebar.date_input("Posting Date Range", value=(postingdate_min, postingdate_max), format="DD/MM/YYYY")

combined_categories = df["categories"].apply(format_category_row_unified).dropna()
unique_category = sorted(combined_categories.unique())
#unique_category = sorted(df["categories"].dropna().unique())
selected_category = st.sidebar.multiselect("Category", unique_category, default=[])

unique_employmentTypes = sorted(df["employmentTypes"].dropna().unique())
selected_employmentTypes = st.sidebar.multiselect("Employment Types", unique_employmentTypes, default=[], key="employment_type")

unique_position = sorted(df["positionLevels"].dropna().unique())
selected_position = st.sidebar.multiselect("Position Level", unique_position, default=[])
min_expYear = df["minimumYearsExperience"].min()
max_expYear = df["minimumYearsExperience"].max()
expYear_range = st.sidebar.slider(
    "Minimum Years of Experience Range",
    min_value=min_expYear,
    max_value=max_expYear,
    value=(min_expYear, max_expYear),
    step=1,
)

unique_salaryType = sorted(df["salary_type"].dropna().unique())
selected_salaryType = st.sidebar.multiselect("Type of Salary", unique_salaryType, default=[])
min_Salary = df["salary_minimum"].min()
max_Salary = df["salary_maximum"].max()
salary_range = st.sidebar.slider(
    "Salary Range",
    min_value=min_Salary,
    max_value=max_Salary,
    value=(min_Salary, max_Salary),
    step=500,
)
# Side Bar - End
# Ended on 4-Nov-2026

st.header("Key Metrics")
# Create four columns for the metrics and unpack them
# We can then use each column to place a metric
metrics_df = df.copy()
col1, col2, col3, col4 = st.columns(4)
#col1
try:
    # Get the raw string from the most common category row
    raw_json_str = metrics_df["categories"].value_counts().index[0]
    
    # Clean up any potential double-escaped quotes and parse the JSON list
    cleaned_str = raw_json_str.replace('""', '"')
    category_list = json.loads(cleaned_str)
    
    # Extract the string "Information Technology"
    top_category = category_list[0]["category"]
except (IndexError, json.JSONDecodeError, KeyError):
    top_category = "No Data"

# --- ADD THIS CSS SNIPPET BEFORE GENERATING YOUR METRICS ---
st.markdown(
    """
    <style>
    /* Targets the metric value (the main text/number) */
    [data-testid="stMetricValue"] {
        font-size: 24px !important; /* Adjust this value down to shrink the size */
    }
    
    /* Targets the metric label (the small text above the value) */
    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1.metric("Top Category", top_category)
col2.metric("Top Position", metrics_df["positionLevels"].value_counts().index[0])
col3.metric("Total Available Job Application", f"{metrics_df[metrics_df['status_jobStatus'].isin(['Open', 'Re-open'])]['metadata_totalNumberJobApplication'].sum():,.0f}")
col4.metric("Average Min. Salary - Max. Salary / Average Salary", f"${metrics_df['salary_minimum'].mean():,.0f} - ${metrics_df['salary_maximum'].mean():,.0f} / ${metrics_df['average_salary'].mean():,.0f}")

st.header("Singapore Jobs Analytics Overview")

# Chart Main Content - Start
# 1. Create the Pie Chart using Plotly Express
filtered_df = df.copy()
st.subheader("Category Breakdown (Grouped)")
if "categories" in df.columns:
    # Extract the nested items out into lists
    # Replace 'category_column' and 'value_column' with your actual CSV headers
    #df["clean_list"] = df["categories"].apply(parse_malformed_json)
    # Explode the lists so each category gets its own independent row row
    #exploded_df = df.explode("clean_list").dropna(subset=["clean_list"])
    filtered_df["combined_string"] = filtered_df["categories"].apply(format_category_row_unified)

    # --- COUNT AND AGGREGATE ---
    category_counts = (
        #exploded_df["clean_list"].value_counts().reset_index()
        filtered_df["combined_string"].value_counts().reset_index()
    )
    category_counts.columns = ["category", "count"]

    # Filter out tiny values < 1% to get rid of the overlapping gray lines in your chart
    total_count = category_counts["count"].sum()
    threshold = total_count * 0.01

    main_categories = category_counts[category_counts["count"] >= threshold]
    other_categories = category_counts[category_counts["count"] < threshold]
    hidden_categories = set(other_categories["category"].tolist())

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

    # Added 4-Nov-2026
    # --- DYNAMIC SELECTION HIGHLIGHTING ---
    pull_values = []
    border_colors = []
    border_widths = []
    for cat in category_counts["category"]:
        if cat == "Others":
            # 2. Check if ANY of the user's selected items are hidden inside "Others"
            # --- Selected Category from Filtering Criteria ---
            if selected_category and any(selected_item in hidden_categories for selected_item in selected_category):
                pull_values.append(0.05)  # Pull out the "Others" slice!
                border_colors.append('#000000')
                border_widths.append(1)
            else:
                pull_values.append(0.0)
                border_colors.append('rgba(0,0,0,0)')  # Transparent
                border_widths.append(0)
        else:
            # Standard matching for main categories
            if selected_category and cat in selected_category:
                pull_values.append(0.05)
                border_colors.append('#000000')
                border_widths.append(1)
            else:
                pull_values.append(0.0)
                border_colors.append('rgba(0,0,0,0)')  # Transparent
                border_widths.append(0)

    fig_pie_category.update_traces(pull=pull_values, marker=dict(
            line=dict(
                color=border_colors,  # Maps individual border color to each slice
                width=border_widths   # Maps individual border width to each slice
            )
        ))
    # Ended on 4-Nov-2026

    st.plotly_chart(fig_pie_category, use_container_width=True)
else:
    st.error("Could not find the 'categories' column.")

# 2. Bar Chart for Position by Category
# --- 2.1 BUILD THE BAR CHART ---
st.subheader("Position for Top 10 Category")
# --- Added on 4-Nov-2026: Selected Position Level from Filtering Criteria ---
if selected_position:
    filtered_df_pos = filtered_df[filtered_df["positionLevels"].isin(selected_position)]
else:
    filtered_df_pos = filtered_df.copy()
# --- 2.2 CLEAN THE JSON CATEGORIES ---
def extract_category_name(json_str):
    try:
        # Fix any double-escaped quotes and parse the JSON string
        cleaned_str = str(json_str).replace('""', '"')
        data = json.loads(cleaned_str)

        # Safely extract the string from the 'category' key
        #if isinstance(data, list) and len(data) > 0:
        #    return data[0].get("category", "Unknown")
        #elif isinstance(data, dict):
        #    return data.get("category", "Unknown")
        if isinstance(data, list):
            categories = [item.get("category", "Unknown") for item in data if isinstance(item, dict)]
            # Join them as a comma-separated string
            return ", ".join(categories) if categories else "Unknown"
        elif isinstance(data, dict):
            return data.get("category", "Unknown")
    except Exception:
        return "Unknown"

# Create a temporary column with clean, plain-text category names
#df_clean = filtered_df.copy()
df_clean = filtered_df_pos.copy()
df_clean["clean_category"] = df_clean["categories"].apply(
    extract_category_name
)

# --- Added on 4-Nov-2026: Selected Category from Filtering Criteria ---
if selected_category:
    df_clean = df_clean[df_clean["clean_category"].isin(selected_category)]
    
# --- 2.3 AGGREGATE THE DATA ---
# Group by the clean text names and count occurrences
count_position_by_category = (
    df_clean.groupby(["positionLevels", "clean_category"])
    .size()
    .reset_index(name="count")
)

# --- 2.4: CALCULATE TRUE TOTALS PER CATEGORY AND FIND TOP 10 ---
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

# --- 2.5 BUILD AND DISPLAY THE PLOTLY BAR CHART ---
fig_category_position = px.bar(
    count_position_by_category,
    x="clean_category",
    y="count",
    color="positionLevels",  # Colors bars by position level (e.g., Senior Management)
    barmode="group",
    labels={"clean_category": "Category", "count": "Position Counts", "positionLevels": "Position Level"},
)

# --- 2.6: FORCE PLOTLY TO RESPECT THE TOTALS SORT ORDER ---
fig_category_position.update_layout(
    xaxis={
        "categoryorder": "array",
        "categoryarray": top_10_categories,  # Enforces biggest total category on the far left
    }
)

# Render the clean chart
st.plotly_chart(fig_category_position, use_container_width=True)

# 3. Bar Chart for Experience by Role Position
# --- 3.1 BUILD THE BAR CHART ---
st.subheader("Minimum Working Experience by Position")

# --- 3.2 AGGREGATE THE DATA ---
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

# --- 3.3 BUILD AND DISPLAY THE PLOTLY BAR CHART ---
fig_position_experience = px.bar(
    count_minexperience_by_position,
    x="positionLevels",
    y="count",
    color="minimumYearsExperience",  # Colors bars by minimum years of experience
    barmode="group",
    labels={"positionLevels": "Position", "count": "Min. of Year Exp. Counts", "minimumYearsExperience": "Years of Minimum Experience"},
)

# --- 3.4: Enforce the total-based sorting order onto the X-axis ---
fig_position_experience.update_layout(
    xaxis={
        "categoryorder": "array", 
        "categoryarray": sorted_positions
    }
)

# Render the clean chart
st.plotly_chart(fig_position_experience , use_container_width=True)

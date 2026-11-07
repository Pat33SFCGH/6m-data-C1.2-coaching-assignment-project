import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="Wide Dashboard", layout="wide")

# Initialize persistent session states to keep track of clicked items
if "clicked_path" not in st.session_state:
    st.session_state.clicked_path = []

# =====================================================================
# 1. DEFINE UTILITY FUNCTIONS
# =====================================================================
@st.cache_data
def load_data(path):
    return pd.read_csv(path, nrows=50000)

def format_category_row_unified(val):
    names = parse_malformed_json(val)
    return ", ".join(names) if names else None

def parse_malformed_json(val):
    if pd.isna(val):
        return []
    try:
        clean_str = str(val).strip()
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]
        clean_str = clean_str.replace('""', '"')
        parsed_list = json.loads(clean_str)
        return [item["category"] for item in parsed_list if "category" in item]
    except Exception:
        return []

# Kindly change to the correct csv file path
DATA_PATH = "./SGJobData.csv"
df = load_data(DATA_PATH)

# Clean data formats
df['categories'] = df['categories'].apply(format_category_row_unified)
df["Job Count"] = 1
df["metadata_newPostingDate"] = pd.to_datetime(df["metadata_newPostingDate"])

df["minimumYearsExperience"] = df["minimumYearsExperience"].fillna(0).astype(int)
df["salary_minimum"] = df["salary_minimum"].fillna(0).astype(float)
df["salary_maximum"] = df["salary_maximum"].fillna(0).astype(float)

# =====================================================================
# 2. SIDE BAR FOR FILTERING CRITERIA
# =====================================================================
st.sidebar.header("Filtering Criteria")

postingdate_min = df["metadata_newPostingDate"].min().date()
postingdate_max = df["metadata_newPostingDate"].max().date()
postingdate_range = st.sidebar.date_input("Posting Date Range", value=(postingdate_min, postingdate_max), format="DD/MM/YYYY")

unique_jobStatus = sorted(df["status_jobStatus"].dropna().unique())
selected_jobStatus = st.sidebar.multiselect("Job Status", unique_jobStatus, default=[])

unique_category = sorted(df["categories"].dropna().unique())
selected_category = st.sidebar.multiselect("Category", unique_category, default=[])

unique_employmentTypes = sorted(df["employmentTypes"].dropna().unique())
selected_employmentTypes = st.sidebar.multiselect("Employment Types", unique_employmentTypes, default=[])

unique_position = sorted(df["positionLevels"].dropna().unique())
selected_position = st.sidebar.multiselect("Position Level", unique_position, default=[])

min_expYear = df["minimumYearsExperience"].min()
max_expYear = df["minimumYearsExperience"].max()
expYear_range = st.sidebar.slider("Minimum Years of Experience", min_value=min_expYear, max_value=max_expYear, value=(min_expYear, max_expYear), step=1)

min_Salary = df["salary_minimum"].min()
#max_Salary = df["salary_maximum"].max()
max_Salary = df["salary_minimum"].max()
salary_range = st.sidebar.slider("Salary Range", min_value=min_Salary, max_value=max_Salary, value=(min_Salary, max_Salary), step=500.0)

# =====================================================================
# 3. APPLY DYNAMIC DATA FILTERING LOGIC
# =====================================================================
df_filtered = df.copy()

if isinstance(postingdate_range, tuple) and len(postingdate_range) == 2:
    start_date, end_date = postingdate_range
    df_filtered = df_filtered[(df_filtered["metadata_newPostingDate"].dt.date >= start_date) & (df_filtered["metadata_newPostingDate"].dt.date <= end_date)]

if selected_jobStatus:
    df_filtered = df_filtered[df_filtered["status_jobStatus"].isin(selected_jobStatus)]
if selected_category:
    df_filtered = df_filtered[df_filtered["categories"].isin(selected_category)]
if selected_employmentTypes:
    df_filtered = df_filtered[df_filtered["employmentTypes"].isin(selected_employmentTypes)]
if selected_position:
    df_filtered = df_filtered[df_filtered["positionLevels"].isin(selected_position)]

df_filtered = df_filtered[(df_filtered["minimumYearsExperience"] >= expYear_range[0]) & (df_filtered["minimumYearsExperience"] <= expYear_range[1])]
df_filtered = df_filtered[(df_filtered["salary_minimum"] >= salary_range[0]) & (df_filtered["salary_minimum"] <= salary_range[1])]

# =====================================================================
# 4. MAIN INTERFACE AND STATE CONTROL
# =====================================================================
st.title("SG Job Analytics Dashboard")

col1, col2, col3, col4 = st.columns(4)
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

col1.metric("Top Category", df_filtered["categories"].value_counts().index[0])
col2.metric("Top Position", df_filtered["positionLevels"].value_counts().index[0])
col3.metric("Total Available Job Application", f"{df_filtered[df_filtered['status_jobStatus'].isin(['Open', 'Re-open'])]['metadata_totalNumberJobApplication'].sum():,.0f}")
col4.metric("Average Min. Salary - Max. Salary / Average Salary", f"${df_filtered['salary_minimum'].mean():,.0f} - ${df_filtered['salary_maximum'].mean():,.0f} / ${df_filtered['average_salary'].mean():,.0f}")

# Dynamic active filters trail
active_path = st.session_state.clicked_path
crumbs = ["🏡 Top Categories"] + active_path
st.subheader(f"📍 Navigation: {' ➔ '.join(crumbs)}")

if active_path:
    if st.button("↩️ Clear Grid Selection & Reset"):
        st.session_state.clicked_path = []
        st.rerun()

col1, col2 = st.columns([3, 2])

if not df_filtered.empty:
    # Filter the exact top-N slices required
    top_5_categories = df_filtered["categories"].value_counts().head(5).index
    df_base_data = df_filtered[df_filtered["categories"].isin(top_5_categories)].copy()

    # Determine what level we display based on history path depth
    if len(active_path) == 0:
        df_grid_source = df_base_data.groupby("categories")["Job Count"].sum().reset_index()
        df_grid_source = df_grid_source.sort_values(by="Job Count", ascending=False)
        current_column = "categories"
        grid_title = "Select a Category Box 👇"
    elif len(active_path) == 1:
        df_sub = df_base_data[df_base_data["categories"] == active_path[0]]
        top_3_pos = df_sub["positionLevels"].value_counts().head(3).index
        df_grid_source = df_sub[df_sub["positionLevels"].isin(top_3_pos)].groupby("positionLevels")["Job Count"].sum().reset_index()
        df_grid_source = df_grid_source.sort_values(by="Job Count", ascending=False)
        current_column = "positionLevels"
        grid_title = f"Select Position Level inside {active_path[0]} 👇"
    else:
        df_sub = df_base_data[
            (df_base_data["categories"] == active_path[0]) & 
            (df_base_data["positionLevels"] == active_path[1])
        ]
        top_2_emp = df_sub["employmentTypes"].value_counts().head(2).index
        df_grid_source = df_sub[df_sub["employmentTypes"].isin(top_2_emp)].groupby("employmentTypes")["Job Count"].sum().reset_index()
        df_grid_source = df_grid_source.sort_values(by="Job Count", ascending=False)
        current_column = "employmentTypes"
        grid_title = f"Employment Breakdown for {active_path[1]} 👇"

    # -----------------------------------------------------------------
    # A. VISUAL GRID BLOCKS ROW (REPLACES BROKEN TREEMAP SELECTIONS)
    # -----------------------------------------------------------------
    with col1:
        st.write(f"### 🔍 {grid_title}")

        # DYNAMIC GO BACK ONE LEVEL CONTROL
        if len(active_path) > 0:
            if st.button("⬅️ Go Back One Level", use_container_width=True):
                st.session_state.clicked_path.pop()  # Removes the last selected level from the trail
                st.rerun()
        
        st.write("---")  # Visual separator line
        
        # Build out dynamic visual block layouts
        for idx, row in df_grid_source.iterrows():
            item_name = str(row[current_column])
            
            # Filter the base data exactly for this item to get matching status counts
            df_item_stats = df_base_data[df_base_data[current_column] == item_name]
            
            total_jobs = len(df_item_stats)
            
            # Extract individual status counts (case-insensitive fallback matching your dictionary)
            open_count = len(df_item_stats[df_item_stats["status_jobStatus"].str.lower() == "open"])
            closed_count = len(df_item_stats[df_item_stats["status_jobStatus"].str.lower() == "closed"])
            reopen_count = len(df_item_stats[df_item_stats["status_jobStatus"].str.lower() == "re-open"])
            
            # Formatted label matching the donut chart metrics perfectly
            button_label = f"📦 {item_name} — ({total_jobs} Jobs | {closed_count} Closed, {open_count} Open, {reopen_count} Re-open)"
            
            # Draw individual block items styled as clean selectable rows
            if st.button(button_label, key=f"grid_btn_{idx}_{len(active_path)}", use_container_width=True):
                if len(active_path) < 2:
                    st.session_state.clicked_path.append(item_name)
                elif len(active_path) == 2:
                    st.session_state.clicked_path.append(item_name)
                elif len(active_path) == 3:
                    st.session_state.clicked_path[-1] = item_name
                
                st.rerun()


    # -----------------------------------------------------------------
    # B. SYNC AND FILTER DONUT DISTRIBUTION
    # -----------------------------------------------------------------
    df_donut_final = df_base_data.copy()
    donut_subtitle = "Based on the Top 5 Categories"
    
    if len(active_path) >= 1:
        df_donut_final = df_donut_final[df_donut_final["categories"] == active_path[0]]
        donut_subtitle = f"Category: {active_path[0]}"
        
    if len(active_path) >= 2:
        df_donut_final = df_donut_final[df_donut_final["positionLevels"] == active_path[1]]
        donut_subtitle += f" ➔ Level: {active_path[1]}"
        
    if len(active_path) >= 3:
        df_donut_final = df_donut_final[df_donut_final["employmentTypes"] == active_path[2]]
        donut_subtitle += f" ➔ Type: {active_path[2]}"

    # -----------------------------------------------------------------
    # C. RENDER DONUT CHART SIDE-BY-SIDE
    # -----------------------------------------------------------------
    with col2:
        st.write("### 📊 Job Status Distribution")
        if not df_donut_final.empty:

            status_colors = {
                "Open": "#2ca02c",     # Green
                "Closed": "#d62728",   # Red
                "Re-open": "#ff7f0e",  # Orange
                "open": "#2ca02c",     # Lowercase fallback
                "closed": "#d62728",   # Lowercase fallback
                "re-open": "#ff7f0e"   # Lowercase fallback
            }

            fig_donut = px.pie(
                df_donut_final, 
                names='status_jobStatus', 
                values='Job Count',
                hole=0.5, 
                title=f"Distribution Profile:<br><sup>{donut_subtitle}</sup>"
            )
            fig_donut.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No distribution records matched this specific filter.")


    # -----------------------------------------------------------------
    # NEW: D. MULTI-VARIABLE SALARY & EXPERIENCE SCATTER PLOT
    # -----------------------------------------------------------------
    st.write("---")
    st.write("### 📈 Salary vs. Experience Breakdown Analysis")

    if not df_donut_final.empty:
        # Group by experience years to get accurate aggregate steps for line drawing
        # 1. Calculate the static overall benchmark constant from the current selection
        overall_benchmark = float(df_donut_final["average_salary"].mean())
        
        # 2. Group min and max salaries by experience years to get the dynamic trend lines
        df_trends = df_donut_final.groupby("minimumYearsExperience")[
            ["salary_minimum", "salary_maximum"]
        ].mean().reset_index()
        
        # 3. Add the constant benchmark value as a fixed column for every experience group row
        df_trends["benchmark_constant"] = overall_benchmark

        # Melt the dataframe to make it compatible with Plotly Express multi-line grouping
        df_melted = df_trends.melt(
            id_vars=["minimumYearsExperience"],
            value_vars=["salary_minimum", "salary_maximum", "benchmark_constant"],
            var_name="Salary Metric",
            value_name="Salary Value"
        )

        # Clean label mapping for the chart legend
        label_mapping = {
            "salary_minimum": "Minimum Salary Line",
            "salary_maximum": "Maximum Salary Line",
            "benchmark_constant": f"Overall Benchmark (Avg: ${overall_benchmark:,.2f})"
        }
        df_melted["Salary Metric"] = df_melted["Salary Metric"].map(label_mapping)

        # Draw the Scatter Chart with Lines connecting the points
        fig_trend = px.line(
            df_melted,
            x="minimumYearsExperience",
            y="Salary Value",
            color="Salary Metric",
            markers=True, # Forces explicit scatter points onto the line paths
            labels={
                "minimumYearsExperience": "Minimum Years of Experience Required",
                "Salary Value": "Monthly Salary Value ($)",
                "Salary Metric": "Salary Type"
            },
            title="Salary Threshold & Benchmark Matrices by Experience Groupings",
            color_discrete_map={
                "Minimum Salary Line": "#1f77b4",                                      # Blue
            "Maximum Salary Line": "#d62728",                                          # Red
                f"Overall Benchmark (Avg: ${overall_benchmark:,.2f})": "#2ca02c"       # Green
            }
        )
        
        # Style lines to make the Benchmark line visually distinct
        fig_trend.update_traces(
            selector=dict(name=f"Overall Benchmark (Avg: ${overall_benchmark:,.2f})"),
            line=dict(width=4, dash="dash"),
            mode="lines" # Hides individual dots/markers on the benchmark so it looks purely flat
        )
        
        fig_trend.update_layout(
            hovermode="x unified", # Shows all 3 values simultaneously on hover alignment
            legend_title_text="Metrics"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient filtered metrics to populate the salary benchmark matrices.")

    # -----------------------------------------------------------------
    # NEW: E. JOB ENGAGEMENT HEATMAP
    # -----------------------------------------------------------------
    # st.write("---")
    # st.write("### 🌡️ Job Engagement Heatmap (Applications vs. Views)")

    # if not df_donut_final.empty:
    #     # Check if the required engagement columns exist in the dataframe
    #     required_cols = ["metadata_totalNumberJobApplication", "categories", "positionLevels"]
    #     missing_cols = [col for col in required_cols if col not in df_donut_final.columns]
        
    #     if not missing_cols:
    #         df_heatmap = df_donut_final.copy()
            
    #         # Ensure application counts are strictly numeric for calculating averages
    #         df_heatmap["metadata_totalNumberJobApplication"] = (
    #             df_heatmap["metadata_totalNumberJobApplication"].fillna(0).astype(float)
    #         )
            
    #         # Handle empty categorization labels gracefully for cleaner visual blocks
    #         df_heatmap["categories"] = df_heatmap["categories"].fillna("Uncategorized")
    #         df_heatmap["positionLevels"] = df_heatmap["positionLevels"].fillna("Unknown Level")

    #         # Generate a clean categorical heatmap matrix using the 'avg' aggregation function
    #         fig_heatmap = px.density_heatmap(
    #             df_heatmap,
    #             x="positionLevels",
    #             y="categories",
    #             z="metadata_totalNumberJobApplication",
    #             histfunc="avg", # Changes color calculation to display the true mathematical mean
    #             labels={
    #                 "positionLevels": "Position Levels",
    #                 "categories": "Job Categories",
    #                 "metadata_totalNumberJobApplication": "Average Applications"
    #             },
    #             title="Average Application Volume Matrix Across Structural Roles",
    #             color_continuous_scale="Plasma" # High-contrast color mapping for density variations
    #         )
            
    #         fig_heatmap.update_layout(
    #             xaxis_title="Position Levels",
    #             yaxis_title="Job Categories",
    #             coloraxis_colorbar=dict(title="Avg Applications"),
    #             hovermode="closest"
    #         )
            
    #         st.plotly_chart(fig_heatmap, use_container_width=True)
            
    #     else:
    #         st.warning(f"Heatmap skipped. Missing columns in dataset: {', '.join(missing_cols)}")
    # else:
    #     st.info("Insufficient metrics available to compute the engagement density heatmap.")

    # -----------------------------------------------------------------
    # UPDATED: E. CONVERSION MATRIX SPOT CIRCLE HEATMAP
    # -----------------------------------------------------------------
    st.write("---")
    st.write("### 🌡️ Job Conversion Matrix (Views vs. Application Conversion)")
    
    if not df_donut_final.empty:
        # Check if all required engagement columns exist in the dataset
        required_cols = ["metadata_totalNumberOfView", "metadata_totalNumberJobApplication", "categories", "positionLevels"]
        missing_cols = [col for col in required_cols if col not in df_donut_final.columns]
        
        if not missing_cols:
            df_heatmap = df_donut_final.copy()
            
            # Clean and format data structures strictly into numeric variants
            df_heatmap["metadata_totalNumberOfView"] = df_heatmap["metadata_totalNumberOfView"].fillna(0).astype(float)
            df_heatmap["metadata_totalNumberJobApplication"] = df_heatmap["metadata_totalNumberJobApplication"].fillna(0).astype(float)
            df_heatmap["categories"] = df_heatmap["categories"].fillna("Uncategorized")
            df_heatmap["positionLevels"] = df_heatmap["positionLevels"].fillna("Unknown Level")

            # Aggregate total metrics grouped by our dimensional matrix points
            df_spot = df_heatmap.groupby(["categories", "positionLevels"]).agg(
                Sum_Views=("metadata_totalNumberOfView", "sum"),
                Sum_Apps=("metadata_totalNumberJobApplication", "sum"),
                Total_Openings=("Job Count", "sum")
            ).reset_index()

            # Prevent divide-by-zero crashes by evaluating records with views
            df_spot["Conversion Rate (%)"] = 0.0
            mask = df_spot["Sum_Views"] > 0
            df_spot.loc[mask, "Conversion Rate (%)"] = (df_spot.loc[mask, "Sum_Apps"] / df_spot.loc[mask, "Sum_Views"]) * 100

            # Generate the dynamic High-View Low-App Identifier Matrix
            fig_spot = px.scatter(
                df_spot,
                x="positionLevels",
                y="categories",
                size="Sum_Views",                 # Circle Size = Total Traffic (Views)
                color="Conversion Rate (%)",       # Circle Color = Conversion Rate (Apps/Views)
                hover_data={
                    "positionLevels": True,
                    "categories": True,
                    "Sum_Views": ":,.0f",          # Nicely formatted view count digits
                    "Sum_Apps": ":,.0f",           # Nicely formatted app count digits
                    "Conversion Rate (%)": ":.2f}%" # Nicely formatted percentage values
                },
                labels={
                    "positionLevels": "Position Levels",
                    "categories": "Job Categories",
                    "Sum_Views": "Total Traffic Views",
                    "Conversion Rate (%)": "Conversion Performance"
                },
                title="Conversion Rates Matrix: Circle Size = Traffic Views | Color Scale = Conversion Rate",
                color_continuous_scale="RdYlGn",  # Red-Yellow-Green: Red = Low Apps/High Views, Green = Balanced
                size_max=35                       # Clear sizing cap boundaries to prevent box clipping
            )
            
            # Restructure structural layout metrics
            fig_spot.update_layout(
                xaxis=dict(type='category', ticks="outside"),
                yaxis=dict(type='category', ticks="outside"),
                xaxis_title="Position Levels",
                yaxis_title="Job Categories",
                coloraxis_colorbar=dict(title="Conversion Rate %"),
                hovermode="closest"
            )
            
            # Overlay light positioning grid lines to isolate single coordinate zones cleanly
            fig_spot.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)')
            fig_spot.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)')
            
            st.plotly_chart(fig_spot, use_container_width=True)
            
        else:
            st.warning(f"Conversion map skipped. Missing metrics in dataset: {', '.join(missing_cols)}")
    else:
        st.info("Insufficient metrics available to compute the conversion spot matrix.")

    # -----------------------------------------------------------------
    # NEW: GENERIC KPI METRIC SUMMARY CARDS
    # -----------------------------------------------------------------
    st.write("---")
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    with kpi_col1:
        # KPI 1: Generic Overall Market Salary Benchmark for current selection
        if not df_filtered.empty and "average_salary" in df_filtered.columns:
            overall_market_avg = float(df_filtered["average_salary"].mean())
            st.metric(
                label="💰 Average Market Salary",
                value=f"${overall_market_avg:,.2f}",
                delta="Based on Active Filters"
            )
        else:
            st.metric(label="💰 Average Market Salary", value="N/A")

    with kpi_col2:
        # KPI 2: Lowest Application Conversion Rate Group within current selection
        df_conv_calc = df_filtered.groupby(["categories", "positionLevels"]).agg(
            Views=("metadata_totalNumberOfView", "sum"),
            Apps=("metadata_totalNumberJobApplication", "sum")
        ).reset_index()
        
        # Filter out rows with zero views to avoid division by zero errors
        df_conv_calc = df_conv_calc[df_conv_calc["Views"] > 0]
        
        if not df_conv_calc.empty:
            df_conv_calc["Rate"] = (df_conv_calc["Apps"] / df_conv_calc["Views"]) * 100
            worst_performing = df_conv_calc.sort_values(by="Rate", ascending=True).iloc[0]
            st.metric(
                label="⚠️ Lowest Conversion Rate Segment",
                value=f"{worst_performing['Rate']:.2f}%",
                delta=f"{worst_performing['positionLevels']} | {worst_performing['categories']}",
                delta_color="inverse"
            )
        else:
            st.metric(label="⚠️ Lowest Conversion Rate Segment", value="N/A")

    with kpi_col3:
        # KPI 3: Identify the segment with the largest volume of Reposts (Re-open status)
        df_reopen = df_filtered[df_filtered["status_jobStatus"].str.lower() == "re-open"]
        
        if not df_reopen.empty:
            df_reopen_grp = df_reopen.groupby(["categories", "positionLevels"]).size().reset_index(name="Count")
            highest_repost_tier = df_reopen_grp.sort_values(by="Count", ascending=False).iloc[0]
            st.metric(
                label="🔄 Top Reposting Segment (Re-open)",
                value=f"{highest_repost_tier['Count']} Listings",
                delta=f"{highest_repost_tier['positionLevels']} | {highest_repost_tier['categories']}",
                delta_color="off"
            )
        else:
            st.metric(label="🔄 Top Reposting Segment (Re-open)", value="0 Listings", delta="No Reposted Jobs")
            
    st.write("---")

else:
    st.info("No records found matching current filtering combinations.")

with st.expander("📋 View Filtered Results Table"):
    if not df_filtered.empty:
        st.dataframe(df_donut_final, use_container_width=True)

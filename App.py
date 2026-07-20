import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. Page Configuration & Aesthetics ---
st.set_page_config(page_title="Lucknow AQI Dashboard", page_icon="🌬️", layout="wide")

# Custom CSS to improve the dashboard's visual hierarchy 
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    div[data-testid="metric-container"] {
        background-color: #F8F9FA;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Title and Description ---
st.title("Air Quality Index (AQI) Monitor")
st.markdown("Analyze daily AQI trends, station-level metrics, and pollutant breakdowns.")

# --- 3. Sidebar: File Uploader ---
st.sidebar.header("Data Configuration")
uploaded_file = st.sidebar.file_uploader("Upload your dataset", type=["csv", "xlsx"])

# Define standard AQI Colors for consistency across all charts
aqi_colors = {
    'Good': '#00E400',
    'Satisfactory': '#FFFF00',
    'Moderate': '#FF7E00',
    'Poor': '#FF0000',
    'Very Poor': '#8F3F97',
    'Severe': '#7E0023'
}

# --- 4. Main App Logic ---
if uploaded_file is not None:
    try:
        # Read the file based on extension
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
            
        # DATA CLEANING: Drop empty 'Unnamed' columns that often export from Excel
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # DATA CLEANING: Standardize the Date column (handles mixed text/datetime formats)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date']) # Remove corrupted rows 
            
        st.success("File uploaded and cleaned successfully!")

        # --- 5. Sidebar Filters ---
        st.sidebar.header("Dashboard Filters")
        
        # Filter by Station (replacing City)
        if 'Recorded_stations' in df.columns:
            selected_stations = st.sidebar.multiselect(
                "Select Stations to Compare:",
                options=df["Recorded_stations"].dropna().unique(),
                default=df["Recorded_stations"].dropna().unique() 
            )
            filtered_df = df[df["Recorded_stations"].isin(selected_stations)]
        else:
            filtered_df = df.copy()

        # Optional Filter by Pollutant
        if 'Prominent_Pollutant' in filtered_df.columns:
            selected_pollutants = st.sidebar.multiselect(
                "Select Prominent Pollutant:",
                options=filtered_df["Prominent_Pollutant"].dropna().unique(),
                default=filtered_df["Prominent_Pollutant"].dropna().unique()
            )
            filtered_df = filtered_df[filtered_df["Prominent_Pollutant"].isin(selected_pollutants)]

        # --- 6. Top Level Metrics ---
        if not filtered_df.empty and 'AQI' in filtered_df.columns:
            avg_aqi = int(filtered_df["AQI"].mean())
            max_aqi = int(filtered_df["AQI"].max())
            
            # Find the most common category using mode
            if 'AQI_Category' in filtered_df.columns:
                most_frequent_category = filtered_df['AQI_Category'].mode()[0]
            else:
                most_frequent_category = "N/A"
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Average AQI", f"{avg_aqi}")
            col2.metric("Highest Recorded AQI", f"{max_aqi}")
            col3.metric("Safety Goal", "100", delta="Target threshold", delta_color="inverse")
            col4.metric("Prevalent Category", f"{most_frequent_category}")
            
            st.divider()

            # --- 7. Enhanced Visualizations ---
            
            # Time Series with Markers
            st.subheader("Time-Series Station Analysis")
            if 'Date' in filtered_df.columns and 'Recorded_stations' in filtered_df.columns:
                # Group by Date and Station to ensure clean lines
                time_df = filtered_df.groupby(['Date', 'Recorded_stations'])['AQI'].mean().reset_index()
                fig_line = px.line(time_df, x="Date", y="AQI", color="Recorded_stations", 
                              title="Daily AQI Trends by Station", markers=True)
                
                # Safety threshold benchmarks
                fig_line.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="Safe Limit (100)")
                fig_line.add_hline(y=300, line_dash="dash", line_color="red", annotation_text="Hazardous (300)")
                
                fig_line.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_line, use_container_width=True)

            # Creating a 2-column layout for the secondary charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("AQI Scatter Distribution")
                if 'AQI_Category' in filtered_df.columns:
                    # Scatter plot maps AQI severity over time using the standard color dictionary
                    fig_scatter = px.scatter(filtered_df, x="Date", y="AQI", color="AQI_Category",
                                             color_discrete_map=aqi_colors,
                                             title="AQI Measurements Over Time",
                                             hover_data=["Recorded_stations", "Prominent_Pollutant"])
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.info("Missing AQI_Category column for Scatter Plot.")

            with col_chart2:
                st.subheader("Category Breakdown")
                if 'AQI_Category' in filtered_df.columns:
                    # Donut chart for category proportions
                    cat_counts = filtered_df['AQI_Category'].value_counts().reset_index()
                    cat_counts.columns = ['AQI_Category', 'Count']
                    fig_donut = px.pie(cat_counts, values='Count', names='AQI_Category', hole=0.4,
                                       color='AQI_Category', color_discrete_map=aqi_colors,
                                       title="Proportion of Air Quality Categories")
                    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_donut, use_container_width=True)
                else:
                    st.info("Missing AQI_Category column for Donut Chart.")

            # Comparative Horizontal Bar Chart
            st.subheader("Overall Average AQI by Station")
            # Calculate averages and sort them so the chart looks organized
            avg_df = filtered_df.groupby("Recorded_stations")["AQI"].mean().reset_index().sort_values(by="AQI")
            
            # Using a horizontal bar chart (orientation='h') is much easier to read for long station names
            fig_bar = px.bar(avg_df, x="AQI", y="Recorded_stations", orientation='h', color="AQI",
                             color_continuous_scale="Reds", title="Average AQI per Station (Sorted)")
            fig_bar.update_traces(texttemplate='%{x:.0f}', textposition='outside')
            fig_bar.update_layout(coloraxis_showscale=False) # Hide the redundant color scale bar
            st.plotly_chart(fig_bar, use_container_width=True)

        else:
            st.warning("Please select at least one station to display data.")

    except Exception as e:
        st.error(f"Error processing the file: {e}")

else:
    st.info("👈 Please upload your file in the sidebar to get started.")

# --- 8. Health Advisories & Standards ---
st.divider()
st.subheader("AQI Health Advisory & Standards (CPCB India)")
            
            # Using tabs to neatly separate standards and actionable measures
tab1, tab2 = st.tabs(["AQI Category Standards", "Actionable Health Measures"])
            
with tab1:
    st.markdown("""
                ### CPCB AQI Categories & Health Impacts
                | AQI Category | AQI Range | Associated Health Impacts |
                | :--- | :--- | :--- |
                | 🟢 **Good** | 0 – 50 | Minimal impact. |
                | 🟡 **Satisfactory** | 51 – 100 | Minor breathing discomfort to sensitive people. |
                | 🟠 **Moderate** | 101 – 200 | Breathing discomfort for people with lung disease, asthma, or heart disease. |
                | 🔴 **Poor** | 201 – 300 | Breathing discomfort is experienced by most people on prolonged exposure. |
                | 🟣 **Very Poor** | 301 – 400 | Respiratory illness on prolonged exposure. |
                | 🟤 **Severe** | 401 – 500 | Affects healthy people; seriously impacts those with existing diseases. |
                """)
                
with tab2:
    st.markdown("""
                ### Suggested Health Measures Based on AQI
                *   **0-100 (Good / Satisfactory):** Ideal for outdoor activities. No specific precautions needed.
                *   **101-200 (Moderate):** People with asthma, heart conditions, or lung disease should limit outdoor activity.
                *   **201-300 (Poor):** The general population is advised to avoid outdoor physical exertion. Sensitive groups should stay indoors.
                *   **301-400 (Very Poor):** Everyone should reduce prolonged outdoor exertion.
                *   **400+ (Severe):** Remain indoors, keep activity levels low, and avoid opening doors and windows during morning and evening hours. 
                """)
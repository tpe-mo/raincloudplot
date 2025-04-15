import streamlit as st
import polars as pl
import plotly.graph_objects as go
import numpy as np
import io
import pandas as pd
from scipy import stats
import pingouin as pg

# Define the configure_plot_layout function at the top
def configure_plot_layout(fig, fig_title, x_axis_label, y_axis_label, group_positions, group_labels, plot_width, plot_height, background_color, grid_color, y_min=None, y_max=None):
    fig.update_layout(
        title=dict(
            text=fig_title,
            font=dict(size=20, family="Arial, sans-serif", color="black"),
            x=0.5,  # Center the title horizontally
            xanchor="center",  # Ensure the title is anchored to the center
            yanchor="top"  # Anchor the title to the top
        ),
        xaxis=dict(
            title=dict(text=x_axis_label, font=dict(size=14, family="Arial, sans-serif", color="black")),
            tickmode='array',
            tickvals=group_positions,
            ticktext=group_labels,
            tickfont=dict(size=12, family="Arial, sans-serif", color="black"),
        ),
        yaxis=dict(
            title=dict(text=y_axis_label, font=dict(size=14, family="Arial, sans-serif", color="black")),
            tickfont=dict(size=12, family="Arial, sans-serif", color="black"),
            gridcolor=grid_color,
            zerolinecolor=grid_color,
            range=[y_min, y_max] if y_min is not None and y_max is not None else None
        ),
        template="simple_white",  # Use a white background template
        margin=dict(l=50, r=40, t=60, b=50),
        width=plot_width,
        height=plot_height,
        plot_bgcolor="white",  # Set plot background to white
        paper_bgcolor="white",  # Set paper background to white
        showlegend=False
    )

# Define color palettes for the plot
COLOR_PALETTES = {
    "Aurora": ["#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"],
    "Neon": ["#ff00ff", "#00ffff", "#ffff00", "#00ff00", "#ff5500", "#0088ff", "#8800ff", "#ff0088"],
    "Monochrome": ["#E0E0E0", "#C0C0C0", "#A0A0A0", "#808080", "#606060", "#404040", "#202020"],
    "Ocean": ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087", "#f95d6a", "#ff7c43", "#ffa600"],
    "Custom": []  # Custom colors can be added dynamically
}

# Set page configuration
st.set_page_config(
    page_title="Raincloud Plot Generator",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌧️"
)

# Apply custom CSS for a dark mode theme
st.markdown("""
<style>
    /* General dark theme styling */
    .stApp {
        background-color: #121212; /* Dark background for the entire app */
        color: #e0e0e0; /* Light text color */
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1e1e1e; /* Dark background for the sidebar */
        border-right: 1px solid #333; /* Subtle border */
    }

    /* Sidebar headers */
    .stSidebar h2, .stSidebar h4 {
        color: #ffffff !important; /* White header text */
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #ffffff !important; /* White headers */
    }
    
    /* Text elements */
    p, label, .stMarkdown {
        color: #e0e0e0 !important; /* Light text color */
        font-size: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

MAX_COLUMNS = 20
SUPPORTED_FILE_TYPES = ["csv", "xlsx", "xls"]

# Sidebar header styling
st.sidebar.markdown("<h2 style='color: #8ab4f8; font-size: 1.5rem; margin-bottom: 1rem;'>Plot Settings</h2>", unsafe_allow_html=True)

# General Settings Section
with st.sidebar.expander("General Settings", expanded=True):
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Figure Dimensions</h4>", unsafe_allow_html=True)
    use_aspect_ratio = st.checkbox("Maintain Aspect Ratio", value=True, key="use_aspect_ratio")
    if use_aspect_ratio:
        xy_ratio = st.slider("Width/Height Ratio", min_value=0.5, max_value=2.0, value=1.0, step=0.1, key="xy_ratio")
        plot_width = st.slider("Plot Width (px)", min_value=200, max_value=1000, value=400, step=10, key="plot_width")
        plot_height = int(plot_width / xy_ratio)
        st.write(f"Calculated Height: {plot_height}px")
    else:
        plot_width = st.slider("Plot Width (px)", min_value=200, max_value=1000, value=400, step=10, key="plot_width")
        plot_height = st.slider("Plot Height (px)", min_value=200, max_value=1000, value=400, step=10, key="plot_height")
    group_spacing = st.slider("Group Spacing", min_value=0.1, max_value=2.0, value=1.0, step=0.1, key="group_spacing")
    
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Labels</h4>", unsafe_allow_html=True)
    fig_title = st.text_input("Figure Title", "Raincloud Plot")
    x_axis_label = st.text_input("X-Axis Label", "Groups")
    y_axis_label = st.text_input("Y-Axis Label", "Values")

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Spacing Settings Section (for gaps between elements)
with st.sidebar.expander("Spacing Settings", expanded=False):
    violin_box_gap = st.slider(
        "Violin to Box Gap", 
        min_value=-0.5,
        max_value=0.5, 
        value=0.0, 
        step=0.01, 
        key="violin_box_gap"
    )
    box_points_gap = st.slider(
        "Box to Points Gap", 
        min_value=-0.5,
        max_value=0.5, 
        value=0.2, 
        step=0.01, 
        key="box_points_gap"
    )

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Element Sizing Section
with st.sidebar.expander("Element Sizing", expanded=False):
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Violin Sizing</h4>", unsafe_allow_html=True)
    violin_width = st.slider("Violin Width", 0.01, 2.0, 0.8, 0.01)
    violin_line_width = st.slider("Violin Outline Width", 0.0, 4.0, 1.0, 0.01)
    
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Box Sizing</h4>", unsafe_allow_html=True)
    box_width = st.slider("Box Width", 0.01, 1.0, 0.3, 0.001)
    box_line_width = st.slider("Box Outline Width", 0.1, 5.0, 1.0, 0.01)
    
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Dots Sizing</h4>", unsafe_allow_html=True)
    point_size = st.slider("Point Size", 2.0, 20.0, 8.0, 0.1)
    point_outline_width = st.slider("Point Outline Width", 0.5, 3.0, 0.5, 0.1)

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Violin Appearance Settings
with st.sidebar.expander("Violin Settings", expanded=False):
    violin_on = st.checkbox("Enable Violin", True)
    if violin_on:
        violin_opacity = st.slider("Violin Opacity", 0.0, 1.0, 0.5, 0.01)
        violin_direction = st.selectbox(
            "Violin Direction",
            ["Left", "Right"],
            index=0,  # Default to "Left"
            key="violin_direction"
        )

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Box Appearance Settings
with st.sidebar.expander("Box Settings", expanded=False):
    box_on = st.checkbox("Enable Box", True)
    if box_on:
        box_opacity = st.slider("Box Opacity", 0.0, 1.0, 1.0, 0.01)

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Dots Appearance Settings
with st.sidebar.expander("Dots Settings", expanded=False):
    points_on = st.checkbox("Enable Dots", True)
    if points_on:
        point_opacity = st.slider("Point Opacity", 0.0, 1.0, 0.8, 0.01)
        point_jitter = st.slider("Point Jitter Width", 0.0, 1.0, 0.2, 0.01)

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Colors Section
with st.sidebar.expander("Colors", expanded=False):
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Theme Selection</h4>", unsafe_allow_html=True)
    color_palette = st.selectbox("Color Palette", list(COLOR_PALETTES.keys()), index=0, key="color_palette")
    if color_palette == "Custom":
        custom_colors = st.text_area("Custom Colors (comma-separated HEX codes)", value="#8ab4f8,#4caf50", key="custom_colors")
        COLOR_PALETTES["Custom"] = [color.strip() for color in custom_colors.split(",")]
    
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Element Colors</h4>", unsafe_allow_html=True)
    violin_color = st.color_picker("Violin Fill Color", "#8ab4f8", key="violin_color")
    violin_outline_color = st.color_picker("Violin Outline Color", "#ffffff", key="violin_outline_color")
    box_color = st.color_picker("Box Fill Color", "#4caf50", key="box_color")
    box_outline_color = st.color_picker("Box Outline Color", "#ffffff", key="box_outline_color")
    points_color = st.color_picker("Points Color", "#4caf50", key="points_color")
    points_outline_color = st.color_picker("Points Outline Color", "#ffffff", key="points_outline_color")
    
    st.markdown("<h4 style='color: #8ab4f8; font-size: 1.2rem;'>Background Colors</h4>", unsafe_allow_html=True)
    background_color = st.color_picker("Plot Background Color", "#121212", key="background_color")
    grid_color = st.color_picker("Grid Line Color", "#333333", key="grid_color")

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Statistical Test Settings Section
with st.sidebar.expander("Statistical Test Settings", expanded=False):
    test_type = st.selectbox(
        "Select Statistical Test",
        ["Welch's T-Test", "Mann-Whitney U Test"],
        index=0,
        key="test_type"
    )

# Y-Axis Scale Settings
with st.sidebar.expander("Y-Axis Scale Settings", expanded=False):
    y_min = st.number_input("Y-Axis Minimum", value=None, step=1.0, format="%.2f", key="y_min")
    y_max = st.number_input("Y-Axis Maximum", value=None, step=1.0, format="%.2f", key="y_max")

# Main content area
st.markdown("<h1 style='text-align: center; color: #8ab4f8;'>Raincloud Plot Generator</h1>", unsafe_allow_html=True)

# Create tabs with improved styling
tabs = st.tabs(["Upload Data", "Help & Instructions"])

with tabs[0]:
    st.markdown("<p style='font-size: 1.1rem;'>Upload your data file to generate a raincloud plot.</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=SUPPORTED_FILE_TYPES)

with tabs[1]:
    st.markdown("""
    <div style='background-color: #1e1e1e; padding: 1.5rem; border-radius: 8px; border: 1px solid #333;'>
        <h3 style='color: #8ab4f8; margin-top: 0;'>Getting Started</h3>
        <ol style='font-size: 1.1rem;'>
            <li><strong>Upload Data:</strong> Select a CSV or Excel file containing your data.</li>
            <li><strong>Configure Plot:</strong> Use the sidebar to customize the appearance of your raincloud plot.</li>
            <li><strong>Export Results:</strong> Download your plot as PNG or SVG, along with statistical summaries.</li>
        </ol>
        
        <h3 style='color: #8ab4f8;'>Data Format</h3>
        <p style='font-size: 1.1rem;'>Your data should be organized with each column representing a group to be plotted. The column headers will be used as group labels.</p>
        
        <h3 style='color: #8ab4f8;'>Statistical Tests</h3>
        <p style='font-size: 1.1rem;'>This tool provides two statistical test options:</p>
        <ul style='font-size: 1.1rem;'>
            <li><strong>Welch's T-Test:</strong> For comparing means when variances may differ</li>
            <li><strong>Mann-Whitney U Test:</strong> Non-parametric test for comparing distributions</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

def load_data(file):
    if file:
        try:
            name = file.name.lower()
            if name.endswith(".csv"):
                return pl.read_csv(file)
            elif name.endswith((".xlsx", ".xls")):
                return pl.read_excel(file)
            else:
                st.error("Unsupported file type. Please upload a CSV or Excel file.")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    return None

# Load and process data if file is uploaded
df = load_data(uploaded_file)

if df is not None:
    columns = df.columns[:MAX_COLUMNS]
    df_melted = df.select(columns).melt(variable_name="Group", value_name="Value")
    df_pd = df_melted.to_pandas()
    
    selected_palette = COLOR_PALETTES[color_palette]
    group_colors = {group: selected_palette[i % len(selected_palette)] for i, group in enumerate(df_pd["Group"].unique())}
    
    st.markdown("<h2 style='color: #8ab4f8; margin-top: 2rem;'>Raincloud Plot</h2>", unsafe_allow_html=True)
    
    # Create plot container with border
    plot_container = st.container()
    plot_container.markdown(
        f"""<div style="padding: 1rem; border-radius: 8px; border: 1px solid #333; background-color: #1a1a1a;">""", 
        unsafe_allow_html=True
    )
    
    with plot_container:
        fig = go.Figure()

        group_positions = [i * group_spacing for i in range(len(df_pd["Group"].unique()))]

        for i, group in enumerate(df_pd["Group"].unique()):
            y = df_pd[df_pd["Group"] == group]["Value"]
            x_base = group_positions[i]
            group_color = group_colors[group]

            if violin_on:
                # Determine the direction of the violin
                side = "negative" if violin_direction == "Left" else "positive"
                violin_fill_color = selected_palette[i % len(selected_palette)]

                fig.add_trace(go.Violin(
                    y=y,
                    x=[x_base] * len(y),
                    name=group,
                    side=side,
                    width=violin_width,
                    opacity=violin_opacity,
                    line=dict(width=violin_line_width, color=violin_outline_color),
                    fillcolor=violin_fill_color,
                    meanline_visible=False,
                    showlegend=False
                ))

            if box_on:
                fig.add_trace(go.Box(
                    y=y,
                    x=[x_base + violin_box_gap] * len(y),
                    name=group,
                    line=dict(color="#000000", width=box_line_width),  # Set outline color to black
                    fillcolor=box_color,
                    boxpoints=False,
                    opacity=box_opacity,
                    width=box_width,
                    showlegend=False
                ))

            if points_on:
                # Ensure dots face the opposite direction of the violin
                jitter_direction = 1 if side == "negative" else -1
                jitter = point_jitter * (np.random.rand(len(y)) - 0.5)
                points_fill_color = selected_palette[(i + 2) % len(selected_palette)]

                fig.add_trace(go.Scatter(
                    y=y,
                    x=x_base + violin_box_gap + (box_points_gap * jitter_direction) + jitter,
                    mode="markers",
                    marker=dict(
                        size=point_size,
                        opacity=point_opacity,
                        color=points_fill_color,
                        line=dict(color=points_outline_color, width=point_outline_width)
                    ),
                    name=group,
                    showlegend=False
                ))

        fig_width_px = plot_width
        fig_height_px = plot_height

        configure_plot_layout(fig, fig_title, x_axis_label, y_axis_label, group_positions, list(df_pd["Group"].unique()), fig_width_px, fig_height_px, background_color, grid_color, y_min, y_max)

        st.plotly_chart(fig, use_container_width=False)

    import shutil  # For checking if pdftops is available

    # Export Options with improved styling
    st.markdown("<h2 style='color: #ffffff; margin-top: 2rem;'>Export Options</h2>", unsafe_allow_html=True)

    try:
        import kaleido  # Ensure kaleido is installed for exporting images
        col1, col2, col3, col4 = st.columns(4)  # Adjust columns to 4 since EPS is removed
        with col1:
            st.download_button(
                "Download PNG",
                fig.to_image(format="png", width=2000, height=2000, scale=1),  # Increase resolution to 2000px
                "raincloud_plot.png",
                "image/png"
            )
        with col2:
            st.download_button(
                "Download SVG",
                fig.to_image(format="svg"),
                "raincloud_plot.svg",
                "image/svg+xml"
            )
        with col3:
            st.download_button(
                "Download PDF",
                fig.to_image(format="pdf"),
                "raincloud_plot.pdf",
                "application/pdf"
            )
        with col4:
            csv_export = df_melted.to_pandas().to_csv(index=False)
            st.download_button(
                "Download Data (CSV)",
                csv_export,
                "raincloud_data.csv",
                "text/csv"
            )
    except ImportError:
        st.warning("Please install `kaleido` using `pip install -U kaleido` to enable image downloads.")
    except Exception as e:
        st.warning(f"Error generating image: {e}")
    
    # Statistical Summary with improved styling
    st.markdown("<h2 style='color: #ffffff; margin-top: 2rem;'>Statistical Summary</h2>", unsafe_allow_html=True)

    # Descriptive Statistics
    descriptive_stats = df_pd.groupby("Group")["Value"].describe().reset_index()

    # Rename columns for better readability
    descriptive_stats.rename(columns={
        "count": "Count",
        "mean": "Mean",
        "std": "Std Dev",
        "min": "Min",
        "25%": "25th Percentile",
        "50%": "Median",
        "75%": "75th Percentile",
        "max": "Max"
    }, inplace=True)

    # Define group names
    group_names = df_pd["Group"].unique()

    # Normality Tests
    normality_results = []
    for group in group_names:
        data = df_pd[df_pd["Group"] == group]["Value"].dropna()
        shapiro_p = stats.shapiro(data).pvalue
        ad_p = stats.anderson(data).critical_values[2]  # Anderson-Darling
        normality_results.append({
            "Group": group,
            "Shapiro-Wilk p": round(shapiro_p, 4),
            "Anderson-Darling p (approx)": round(ad_p, 4)
        })
    normality_results = pd.DataFrame(normality_results)

    # Pairwise Statistical Tests
    ttest_results = []
    bayes_results = []

    for i in range(len(group_names)):
        for j in range(i + 1, len(group_names)):
            g1 = group_names[i]
            g2 = group_names[j]
            data1 = df_pd[df_pd["Group"] == g1]["Value"].dropna()
            data2 = df_pd[df_pd["Group"] == g2]["Value"].dropna()

            if len(data1) > 1 and len(data2) > 1:
                if test_type == "Welch's T-Test":
                    # Perform Welch's T-Test
                    ttest = pg.ttest(data1, data2, paired=False, alternative="two-sided")
                    t_stat = ttest['T'].values[0]
                    p_value = ttest['p-val'].values[0]
                    cohen_d = ttest['cohen-d'].values[0]

                    ttest_results.append({
                        "Group 1": g1,
                        "Group 2": g2,
                        "T-stat": round(t_stat, 4),
                        "P-value": round(p_value, 4),
                        "Cohen's d": round(cohen_d, 4)
                    })

                    # Perform Bayesian T-Test
                    n1 = len(data1)
                    n2 = len(data2)
                    bayes_factor = pg.bayesfactor_ttest(t_stat, nx=n1, ny=n2, alternative="two-sided")
                    bayes_results.append({
                        "Group 1": g1,
                        "Group 2": g2,
                        "Bayes Factor": round(bayes_factor, 4)
                    })
                elif test_type == "Mann-Whitney U Test":
                    # Perform Mann-Whitney U Test
                    mannwhitney = pg.mwu(data1, data2, alternative="two-sided")
                    u_stat = mannwhitney['U-val'].values[0]
                    p_value = mannwhitney['p-val'].values[0]

                    ttest_results.append({
                        "Group 1": g1,
                        "Group 2": g2,
                        "U-stat": round(u_stat, 4),
                        "P-value": round(p_value, 4)
                    })

    # Display Results
    st.markdown("<h3 style='color: #ffffff;'>Descriptive Statistics</h3>", unsafe_allow_html=True)
    st.dataframe(descriptive_stats)

    st.markdown("<h3 style='color: #ffffff;'>Normality Test Results</h3>", unsafe_allow_html=True)
    st.dataframe(normality_results)

    st.markdown(f"<h3 style='color: #ffffff;'>{test_type} Results</h3>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(ttest_results))

    if test_type == "Welch's T-Test":
        st.markdown("<h3 style='color: #ffffff;'>Bayesian T-Test Results</h3>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(bayes_results))
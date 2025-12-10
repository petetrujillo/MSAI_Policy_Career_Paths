import streamlit as st
import json
import os
import textwrap
import urllib.parse
import google.generativeai as genai
from streamlit_agraph import agraph, Node, Edge, Config

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Purdue AI Policy Career Mapper")

# --- CSS for Styling ---
st.markdown("""
<style>
    /* FORCE GLOBAL BLACK BACKGROUND */
    .stApp {
        background-color: #000000;
        color: #FAFAFA; /* Ensures text is visible */
    }

    /* Card Styling */
    .deep-dive-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #4B4B4B;
        color: #FAFAFA;
        height: 100%;
    }
    .deep-dive-card p {
        margin-bottom: 10px;
        line-height: 1.4;
        font-size: 0.95em;
    }
    .highlight-title {
        color: #FF4B4B;
        font-weight: bold;
        font-size: 1.0em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .warning-box {
        background-color: #2d2222;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        color: #ffcfcf;
        font-size: 0.9em;
        margin-bottom: 20px;
    }
    /* Button Tweaks */
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. State Management ---
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None
if 'token_usage' not in st.session_state:
    st.session_state.token_usage = 0
if 'should_fetch' not in st.session_state:
    st.session_state.should_fetch = False

# --- 2. Google Gemini Setup ---
def get_gemini_response(filters):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY not found! Check your Streamlit Secrets.")
        return None

    genai.configure(api_key=api_key)

    # --- UPDATED LOGIC FOR BROAD CAREER PATHS ---
    system_instruction = f"""
    You are a Career Strategist specialized in the "Purdue Masters of AI Policy and Management" program.
    
    CONTEXT:
    The user is a graduate looking for realistic career entry points in: {filters['industry']}.
    The user is open to roles in: {filters['style']}.
    
    CRITICAL INSTRUCTION:
    - DO NOT limit results to "AI Governance" or "Policy" titles. 
    - A Master's degree alone is rarely a golden ticket. You must find roles where this degree acts as a specific *differentiator* (e.g., Product Management, Compliance, Strategy, Risk, Technical Sales).
    - The "Certifications" layer is VITAL. It must answer: "What specific credential makes this Policy grad hireable for this specific hard-skill role?"

    TASK:
    1. CENTER NODE: "Purdue AI Policy Grad"
    2. LAYER 1 (Connections): Identify 5 distinct, broad Job Titles. Mix "Direct" matches (Policy) with "Pivot" matches (e.g. PM, Risk Analyst) suitable for the {filters['industry']} sector.
    3. LAYER 2 (Sub-connections): For EACH Job Title, identify 2-3 specific Professional Certifications (e.g., CIPP, CISSP, PMP, AWS Certified Practitioner) that provide the hard credibility needed to land that job.

    OUTPUT JSON STRUCTURE:
    {{
        "center_node": {{
            "name": "Purdue MS AI Policy",
            "type": "Degree",
            "mission": "Your degree is the foundation, but certifications are your bridge to industry.",
            "positive_news": "Versatile degree for hybrid roles.",
            "red_flags": "Requires hard-skill proof (certs) to compete."
        }},
        "connections": [
            {{
                "name": "Job Title A",
                "reason": "Why is this a good fit? (e.g., 'Uses your ethics background to manage product risk')",
                "sub_connections": [
                    {{"name": "Certification X", "reason": "Why this specific cert? (e.g., 'Proves you know the privacy laws')"}},
                    {{"name": "Certification Y", "reason": "Why this specific cert? (e.g., 'Proves technical competency')"}}
                ]
            }}
        ]
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        with st.spinner(f"🔍 Mapping Career Trajectories..."):
            response = model.generate_content(system_instruction)
        
        input_tokens = len(system_instruction) / 4
        output_tokens = len(response.text) / 4
        st.session_state.token_usage += (input_tokens + output_tokens)

        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
        
    except Exception as e:
        st.error(f"AI Analysis Error: {e}")
        return None

# --- 3. Sidebar Controls ---
with st.sidebar:
    st.title("Purdue AI Policy Mapper")
    st.markdown("Explore broad career trajectories and the certifications that could support them. Note: this is generated using Gemini LLM, so there can be mistakes, but the results may spark your own inspiration to do more of your own research!")
    st.divider()
    
    # Hunter Filters
    st.subheader("🎯 Career Scope")
    f_industry = st.selectbox("Target Sector", 
        ["Any", "Government / Public Sector", "Big Tech (FAANG)", "Consulting (Big 4)", "Nonfit / NGO", "Defense & Aerospace", "Financial Services", "Healthcare", "Consumer Tech"])
    
    f_style = st.selectbox("Role Function", 
        ["Any", "Product & Strategy", "Risk & Compliance", "Policy & Research", "Technical Program Mgmt", "Trust & Safety"])

    st.divider()

    # Primary Action
    if st.button("🚀 Generate Paths", type="primary", key="launch_btn"):
        st.session_state.should_fetch = True
        st.session_state.graph_data = None # Clear old data on new click
        st.rerun()

    # Clear
    if st.button("🗑️ Clear Map"):
        st.session_state.graph_data = None
        st.session_state.token_usage = 0
        st.session_state.should_fetch = False
        st.rerun()

# --- 4. Main Logic ---
filters = {"industry": f_industry, "style": f_style}

if st.session_state.should_fetch:
    data = get_gemini_response(filters)
    if data:
        st.session_state.graph_data = data
        st.session_state.should_fetch = False # Reset
        st.rerun()

# --- 5. Layout Rendering ---
data = st.session_state.graph_data

if data:
    center_info = data['center_node']
    connections = data['connections']

    # --- CENTER COLUMN: Graph ---
    # Build Graph
    nodes = []
    edges = []
    node_ids = set()

    # Center Node (The Degree)
    nodes.append(Node(
        id=center_info['name'], 
        label=center_info['name'], 
        size=45, 
        color="#B19CD9", 
        font={'color': 'white'},
        shape="dot"
    ))
    node_ids.add(center_info['name'])

    for item in connections:
        # Layer 1: Job Titles
        if item['name'] not in node_ids:
            nodes.append(Node(
                id=item['name'], 
                label=item['name'], 
                size=30, 
                color="#FF4B4B", 
                font={'color': 'white'}, # Ensure text is white
                title=item['reason']
            ))
            node_ids.add(item['name'])
        
        edges.append(Edge(
            source=center_info['name'], 
            target=item['name'], 
            color="#808080",
            width=3
        ))

        # Layer 2: Certifications
        if 'sub_connections' in item:
            for sub in item['sub_connections']:
                if sub['name'] not in node_ids:
                    nodes.append(Node(
                        id=sub['name'], 
                        label=sub['name'], 
                        size=20, 
                        color="#00C0F2", 
                        font={'color': 'white'}, # Ensure text is white
                        title=f"Cert for {item['name']}: {sub['reason']}",
                        shape="diamond"
                    ))
                    node_ids.add(sub['name'])
                
                edges.append(Edge(
                    source=item['name'], 
                    target=sub['name'], 
                    color="#404040", 
                    width=1,
                    dashes=True
                ))

    # --- CONFIG UPDATE HERE ---
    config = Config(
        width=1200,
        height=600,
        directed=True, 
        physics=True, 
        hierarchical=False, 
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=True,
        backgroundColor="#000000"  # <--- This fixes the white box
    )

    col_main, col_right = st.columns([3, 1])
    
    with col_main:
        st.subheader(f"Career Map: {filters['industry']}")
        clicked_node = agraph(nodes=nodes, edges=edges, config=config)

    # --- RIGHT COLUMN: Details ---
    with col_right:
        st.subheader("📝 Path Details")
        
        selected_node_name = clicked_node if clicked_node else center_info['name']
        
        display_text = ""
        display_sub = ""
        
        if selected_node_name == center_info['name']:
            display_text = center_info['mission']
            display_sub = "Select a red node (Job) to see details, or a blue diamond (Cert) for requirements."
        else:
            found = False
            for c in connections:
                if c['name'] == selected_node_name:
                    display_text = c['reason']
                    display_sub = "Top Recommended Certifications:"
                    for sub in c.get('sub_connections', []):
                        display_sub += f"\n- {sub['name']}"
                    found = True
                    break
                for sub in c.get('sub_connections', []):
                    if sub['name'] == selected_node_name:
                        display_text = sub['reason']
                        display_sub = f"Critical credibility booster for: {c['name']}"
                        found = True
                        break
            if not found:
                display_text = "Node details not found."

        st.info(f"**{selected_node_name}**")
        st.write(display_text)
        if display_sub:
            st.markdown(f"_{display_sub}_")
            
        st.divider()
        if selected_node_name != center_info['name']:
            query = urllib.parse.quote(f"{selected_node_name} {filters['industry']} certification requirements")
            st.link_button("🔎 Research Requirements", f"https://www.google.com/search?q={query}")

else:
    # Landing State
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <h1>🎓 Welcome, Purdue Graduates</h1>
        <p>Select your target industry and preferred role function on the left.</p>
        <p style="font-size: 0.9em; color: #888;">We will map diverse career paths and the specific certifications you need to be credible in them.</p>
    </div>
    """, unsafe_allow_html=True)

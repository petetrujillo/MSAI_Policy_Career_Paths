import streamlit as st
import json
import os
import textwrap
import urllib.parse
import google.generativeai as genai
from streamlit_agraph import agraph, Node, Edge, Config

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Purdue AI Career Mapper")

# --- CSS for Styling ---
st.markdown("""
<style>
    /* ADAPTIVE CARD STYLING */
    .deep-dive-card {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
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
    
    /* ATTEMPT TO FORCE GRAPH BACKGROUND */
    iframe {
        background-color: #0e1117 !important;
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
if 'session_cost' not in st.session_state:
    st.session_state.session_cost = 0.0
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

    # --- DYNAMIC PROMPT LOGIC BASED ON TRACK ---
    if filters['track'] == "AI Management & Policy":
        program_context = """
        DEGREE PROFILE: 'AI Management & Policy' Track.
        - GRADUATE PERSONA: Strategic Leader, Governance Expert, Product Visionary.
        - KEY STRENGTHS: Bridging the gap between technical teams and business goals, Ethics, Policy, Risk Management.
        - AVOID: Do not suggest purely coding-heavy roles (like Core Developer) unless they have a strategic component.
        """
        center_node_name = "Purdue Policy Grad"
        
    else: # AI & Machine Learning
        program_context = """
        DEGREE PROFILE: 'AI and Machine Learning' Track.
        - GRADUATE PERSONA: Technical Builder, Model Architect, Data Scientist.
        - KEY STRENGTHS: Python, TensorFlow, NLP, Computer Vision, building and deploying models.
        - AVOID: Do not suggest purely non-technical administrative roles.
        """
        center_node_name = "Purdue ML Grad"

    system_instruction = f"""
    You are a Career Strategist specialized in the Purdue Masters of AI program.
    
    {program_context}
    
    USER CONSTRAINTS:
    - Target Industry: {filters['industry']}
    - Preferred Role Function: {filters['style']}
    
    TASK:
    1. CENTER NODE: "{center_node_name}"
    2. LAYER 1 (Job Titles): GENERATE 5 distinct job titles that fit the "{filters['track']}" profile within the {filters['industry']} industry.
       - BE CREATIVE: Look for modern, emerging titles (e.g., "AI Audit Manager" or "ML Ops Engineer").
    3. LAYER 2 (Certifications): For EACH job title, GENERATE 2-3 specific, high-value certifications that would help a candidate land THAT specific job.
       - CRITICAL: The certifications must be relevant to the specific job node.

    OUTPUT JSON STRUCTURE:
    {{
        "center_node": {{
            "name": "{center_node_name}",
            "type": "Degree",
            "mission": "Career Map for the {filters['track']} track in {filters['industry']}.",
            "positive_news": "Why this degree profile is valuable right now.",
            "red_flags": "One skill gap to watch out for."
        }},
        "connections": [
            {{
                "name": "Generated Job Title",
                "reason": "Why this fits the degree profile?",
                "sub_connections": [
                    {{"name": "Specific Cert A", "reason": "Why this cert?"}},
                    {{"name": "Specific Cert B", "reason": "Why this cert?"}}
                ]
            }}
        ]
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        with st.spinner(f"🔍 Analyzing Career Paths for {filters['track']}..."):
            response = model.generate_content(system_instruction)
        
        input_tokens = len(system_instruction) / 4
        output_tokens = len(response.text) / 4
        st.session_state.token_usage += (input_tokens + output_tokens)
        st.session_state.session_cost += 0.003

        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
        
    except Exception as e:
        st.error(f"AI Analysis Error: {e}")
        return None

# --- 3. Sidebar Controls ---
with st.sidebar:
    st.title("Purdue AI Career Mapper")
    
    # --- UPDATED TABS: Added Model Card ---
    tab_main, tab_about, tab_model = st.tabs(["🚀 Controls", "ℹ️ About", "🧠 Model Card"])
    
    # --- TAB 1: CONTROLS ---
    with tab_main:
        st.markdown("Generate career paths customized to your specific Master's track.")
        st.divider()
        
        st.subheader("🎓 Degree Track")
        f_track = st.radio("Select your specialization:", 
            ["AI Management & Policy", "AI and Machine Learning"],
            index=0,
            help="This changes the AI's logic to focus on either Strategy/Governance or Technical/Engineering roles."
        )
        
        st.divider()
        st.subheader("🎯 Career Scope")
        f_industry = st.selectbox("Target Sector", 
            ["Any", "Government / Public Sector", "Big Tech (FAANG)", "Consulting (Big 4)", "Nonfit / NGO", "Defense & Aerospace", "Financial Services", "Healthcare", "Consumer Tech"])
        
        f_style = st.selectbox("Role Function", 
            ["Any", "Product & Strategy", "Risk & Compliance", "Policy & Research", "Technical Program Mgmt", "Trust & Safety", "Engineering & Dev", "Data Science"])

        st.divider()

        if st.button("🚀 Generate Paths", type="primary", key="launch_btn"):
            st.session_state.should_fetch = True
            st.session_state.graph_data = None 
            st.rerun()

        if st.button("🗑️ Clear Map"):
            st.session_state.graph_data = None
            st.session_state.should_fetch = False
            st.rerun()
        
        st.divider()
        st.caption("Session Monitor")
        st.metric("Total Cost", f"${st.session_state.session_cost:.3f}", help="Calculated at ~$0.003 per query")

    # --- TAB 2: ABOUT ---
    with tab_about:
        st.subheader("About the Creator")
        st.markdown("Built by **Pete Trujillo** to help Purdue students visualize career possibilities beyond standard paths.")
        
        st.markdown("### 🌐 Connect")
        st.link_button("🏠 PeteTrujillo.com", "https://petetrujillo.com")
        st.link_button("🍀 DoubleLucky.ai (Non-Profit)", "https://doublelucky.ai")
        st.link_button("🐙 GitHub Repo", "https://github.com/petetrujillo/MSAI_Policy_Career_Paths")
        
        st.divider()
        st.markdown("### ☕ Support the Project")
        st.markdown(
            """
            <div style="text-align: center;">
                <a href="https://buymeacoffee.com/petetru" target="_blank">
                    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 45px !important;width: 162px !important;" >
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --- TAB 3: MODEL CARD ---
    with tab_model:
        st.subheader("🧠 Model Card")
        st.caption("Transparency on how this tool works.")
        
        st.markdown("""
        **Project:** Purdue AI Career Mapper  
        **Model Engine:** Google Gemini 1.5 Flash  
        **Purpose:** To map academic degrees to industry roles and required certifications.

        #### 🎯 Intended Use
        * **Primary Users:** Students/Alumni of Purdue MS in AI.
        * **Goal:** Career exploration and strategic planning.
        * **Mechanism:** Generates a 3-layer knowledge graph (Degree → Jobs → Certifications).

        #### ⚙️ How It Works
        The model uses two distinct "System Personas" based on your selected track:

        | Track | **Management & Policy** | **AI & Machine Learning** |
        | :--- | :--- | :--- |
        | **Persona** | Strategic Leader, Governance Expert | Technical Builder, Data Scientist |
        | **Focus** | Bridging business & tech, Ethics, Risk | Coding, Model Deployment, Math |
        | **Output** | Roles like *AI Ethics Officer*, *PM* | Roles like *ML Ops Engineer*, *Dev* |

        #### ⚠️ Limitations
        * **Hallucination Risk:** AI may occasionally suggest deprecated certifications.
        * **Knowledge Cutoff:** Suggestions are based on the model's training data cutoff.
        * **Advisory:** Always verify exam requirements (costs, prerequisites) independently. This tool is for **exploration**, not financial advice.
        """)

# --- 4. Main Logic ---
filters = {"industry": f_industry, "style": f_style, "track": f_track}

if st.session_state.should_fetch:
    data = get_gemini_response(filters)
    if data:
        st.session_state.graph_data = data
        st.session_state.should_fetch = False 
        st.rerun()

# --- 5. Layout Rendering ---
data = st.session_state.graph_data

if data:
    center_info = data['center_node']
    connections = data['connections']

    # --- CENTER COLUMN: Graph ---
    nodes = []
    edges = []
    node_ids = set()

    # Define High-Contrast Font
    high_contrast_font = {
        'color': 'white',
        'strokeWidth': 4,       
        'strokeColor': 'black'  
    }

    # Center Node (The Degree)
    nodes.append(Node(
        id=center_info['name'], 
        label=center_info['name'], 
        size=45, 
        color="#B19CD9", 
        font=high_contrast_font, 
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
                font=high_contrast_font, 
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
                        font=high_contrast_font, 
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

    # Config
    config = Config(
        width=1200,
        height=600,
        directed=True, 
        physics=True, 
        hierarchical=False, 
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=True,
        backgroundColor="#0e1117" 
    )

    col_main, col_right = st.columns([3, 1])
    
    with col_main:
        st.subheader(f"Career Map: {filters['track']} in {filters['industry']}")
        st.warning("⚠️ **AI Generated Advisory:** Verify all role availability and requirements independently.")
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

        # Adaptive Card
        st.markdown(f"""
        <div class="deep-dive-card">
            <div class="highlight-title">{selected_node_name}</div>
            <p>{display_text}</p>
            <p><i>{display_sub}</i></p>
        </div>
        """, unsafe_allow_html=True)
            
        st.divider()
        if selected_node_name != center_info['name']:
            query = urllib.parse.quote(f"{selected_node_name} {filters['industry']} certification requirements")
            st.link_button("🔎 Research Requirements", f"https://www.google.com/search?q={query}")

else:
    # Landing State
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <h1>🎓 Welcome, Purdue Graduates</h1>
        <p>Select your Degree Track and Target Industry on the left.</p>
        <p style="font-size: 0.9em; color: gray;">We will map diverse career paths and the specific certifications you need to be credible in them.</p>
    </div>
    """, unsafe_allow_html=True)

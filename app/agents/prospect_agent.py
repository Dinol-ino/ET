from langgraph.graph import StateGraph
from app.integrations.llm_client import generate_response

def fetch_data(state):
    company = state["company_name"]
    state["data"] = f"Basic info about {company}"
    return state

def analyze(state):
    prompt = f"""
    Analyze this company: {state['data']}
    Give industry, summary, and score out of 100.
    """
    result = generate_response(prompt)
    state["analysis"] = result
    return state

def generate_email(state):
    prompt = f"""
    Write a personalized cold email for:
    {state['analysis']}
    """
    email = generate_response(prompt)
    state["email"] = email
    return state


def build_graph():
    builder = StateGraph(dict)

    builder.add_node("fetch", fetch_data)
    builder.add_node("analyze", analyze)
    builder.add_node("email", generate_email)

    builder.set_entry_point("fetch")
    builder.add_edge("fetch", "analyze")
    builder.add_edge("analyze", "email")

    return builder.compile()
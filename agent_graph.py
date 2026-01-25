import operator
from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    # The user's original query
    query: str
    
    # Classification of intent (router result)
    intent: str # 'analyst', 'researcher', 'strategist'
    
    # Internal context found by agents (e.g. dates from researcher)
    context: Annotated[List[str], operator.add]
    
    # Final response or partial results
    results: Annotated[List[dict], operator.add]
    
    # The final consolidated answer to show the user
    final_answer: str

def create_graph():
    workflow = StateGraph(AgentState)

    # 1. Define Nodes (Logic will be imported from agents/)
    # For now, these are placeholders
    
    def router_node(state: AgentState):
        # Logic to decide next step
        return {"intent": "analyst"}

    def analyst_node(state: AgentState):
        return {"results": [{"source": "analyst", "data": "SQL Result Placeholder"}]}

    def researcher_node(state: AgentState):
        return {"context": ["Fact: Blackout happened on 2025-05-15"]}

    def strategist_node(state: AgentState):
        return {"results": [{"source": "strategist", "data": "Bundle Suggestion Placeholder"}]}

    # 2. Add Nodes to Graph
    workflow.add_node("router", router_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("strategist", strategist_node)

    # 3. Define Edges (Routing Logic)
    workflow.set_entry_point("router")
    
    def route_decision(state: AgentState):
        return state["intent"]

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "analyst": "analyst",
            "researcher": "researcher",
            "strategist": "strategist"
        }
    )

    workflow.add_edge("researcher", "analyst") # Researcher typically feeds Analyst
    workflow.add_edge("analyst", END)
    workflow.add_edge("strategist", END)

    return workflow.compile()

# Singleton instance of the graph
graph = create_graph()

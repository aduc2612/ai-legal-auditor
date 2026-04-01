from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from typing import Literal, Annotated
from typing_extensions import TypedDict
import operator

from dotenv import load_dotenv

from vector import retriever, dataset
from schema import AuditResults, Flags

SYSTEM_PROMPT = """
You are a professional lawyer with decades of experience in identifying risks in legal contracts.
Identify risky clauses in the user's contract, based on the provided examples from the user.
Keep it clear and concise.
Focus on facts and information.
Use objective, neutral tone.
Give helpful suggestions to the user for their best interests.
Be strict.
Identify risks using evidence, not personal thoughts.
"""

load_dotenv()

# model = ChatGroq(
#     model="openai/gpt-oss-20b"
# )

from langchain_ollama import ChatOllama

model = ChatOllama(
    model="llama3.2:3b"
)



class State(TypedDict):
    messages: Annotated[list, add_messages]
    flags: list[Flags]

def flag_node(state: State):
    last_message = state["messages"][-1]
    flags_model = model.with_structured_output(AuditResults)

    clauses = retriever.invoke(last_message.content)

    print(clauses)
    
    result = flags_model.invoke([
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"""
                    Here are some examples of risky clauses: {clauses}
                    Identify risks in my contract: {last_message.content}
"""
        }
    ])

    return {"flags": result.items}


def approval_node(state: State)-> Command[Literal["proceed_node", "flag_node"]]:
    is_approved = interrupt({
        "flags": state["flags"]
    })

    if is_approved:
        return Command(goto="proceed_node")
    return Command(goto="flag_node")

def proceed_node(state: State):
    if state["flags"] == []:
        return {"messages": [{"role": "assistant", "content": "No risks found"}]}
    assistant_message = ""
    for flag in state["flags"]:
        assistant_message = assistant_message + f"\n{flag.clause_type}: {flag.issue}\nSeverity: {flag.severity}\nSuggestions: {flag.suggestion}"
    return {"messages": [{"role": "assistant", "content": assistant_message}]}


checkpointer = InMemorySaver()
graph = (
    StateGraph(State)
    .add_node("flag_node", flag_node)
    .add_node("approval_node", approval_node)
    .add_node("proceed_node", proceed_node)
    .add_edge(START, "flag_node")
    .add_edge("flag_node", "approval_node")
    .add_edge("proceed_node", END)
).compile(checkpointer=checkpointer)
config: RunnableConfig = {"configurable": {"thread_id": "1"}}

def run_chatbot():
    config = {"configurable": {"thread_id": "1"}}

    while True:
        user_input = input("User (q to exit): ")
        if user_input == "q": break
        

        idx = int(user_input)
        contract_text = dataset["data"][idx]["paragraphs"][0]["context"]

        input_data = {"messages": [{"role": "user", "content": contract_text}]}

        approved = "n"

        while approved == "n":

        
            result = graph.invoke(input_data, config=config)

            print("\n--- AI IDENTIFIED RISKS ---")
            for f in result["flags"]:
                print(f"- {f.clause_type}: {f.issue} ({f.severity})")

            approved = input("\nApprove these flags? (y/n): ")
            
            # Resume: The graph picks up exactly where it left off
            if approved == "y":
                final_state = graph.invoke(
                    Command(resume=True), 
                    config=config
                )
            else:
                graph.invoke(Command(resume=False), config=config)

        print(f"Assistant: {final_state['messages'][-1].content}")


if __name__ == "__main__":
    run_chatbot()
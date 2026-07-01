import sys
sys.path.insert(0, '.')
import asyncio, threading, time
from tools.flight_tools import search_flights

# Simulate LangGraph parallel node execution (each node runs in a thread
# because LangGraph sends nodes to concurrent tasks)

results = []
errors = []

def run_flight_search(node_id):
    try:
        r = search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
        results.append((node_id, r))
    except Exception as e:
        errors.append((node_id, e))

# Inside LangGraph, nodes run concurrently in the same event loop.
# `_run_coroutine` would detect the running loop and go to the
# daemon-thread path. Multiple parallel calls = multiple daemon threads.
print('=== Test 1: Parallel calls from threads with running loops ===')
threads = []
for i in range(3):
    def make_node(n):
        def _run():
            # Simulate being inside LangGraph: create event loop first
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # search_flights will see a running loop and use daemon thread path
                r = search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
                results.append((n, r))
            except Exception as e:
                errors.append((n, e))
            finally:
                loop.close()
        return _run
    t = threading.Thread(target=make_node(i), daemon=True)
    threads.append(t)

for t in threads:
    t.start()
for t in threads:
    t.join()

print(f'Results: {len(results)}, Errors: {len(errors)}')
for node_id, r in results:
    print(f'  Node {node_id}: status={r.get("status")}')
    if r.get('status') == 'error':
        err = r.get('error', '')
        if isinstance(err, str) and 'ExceptionGroup' in err:
            print('    -> ExceptionGroup (tool name mismatch, not asyncio error)')
        else:
            print(f'    -> {str(err)[:200]}')

for node_id, e in errors[:2]:
    print(f'  CRASH node {node_id}: {type(e).__name__}: {str(e)[:200]}')

print()
print('=== Test 2: Calls from a thread WITH a running event loop ===')
def from_running_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        r = search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
        print(f'Result: status={r.get("status")}')
        if r.get('status') == 'error':
            err = r.get('error', '')
            if isinstance(err, str) and 'no running event loop' in err:
                print(f'  -> HAS asyncio error: {err[:300]}')
            elif isinstance(err, str) and 'ExceptionGroup' in err:
                print(f'  -> ExceptionGroup (tool mismatch): {err[:300]}')
            else:
                print(f'  -> Other error: {str(err)[:300]}')
    except Exception as e:
        print(f'Crash: {type(e).__name__}: {str(e)[:200]}')
    finally:
        loop.close()

t2 = threading.Thread(target=from_running_loop, daemon=True)
t2.start()
t2.join()

print()
print('=== Test 3: LangGraph simulation with parallel Send ===')
# The Send() function routes to multiple nodes that run in parallel
# inside the same event loop. Each node calls its tool function.
# This is what actually happens in the real application.
import langgraph.graph as lg
from langgraph.graph import StateGraph, START, Send
from typing import TypedDict, Annotated, Literal
import operator

class TestState(TypedDict):
    messages: list
    flight_results: Annotated[list, operator.add]
    next: str

def route_test(state):
    return [Send('flight1', {'messages': state['messages'], 'flight_results': [], 'next': ''}),
            Send('flight2', {'messages': state['messages'], 'flight_results': [], 'next': ''})]

def flight1(state):
    r = search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
    return {'flight_results': [{'node': 'flight1', 'result': r}]}

def flight2(state):
    r = search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
    return {'flight_results': [{'node': 'flight2', 'result': r}]}

def join(state):
    return {'messages': state['messages'] + ['done'], 'next': '__end__'}

builder = StateGraph(TestState)
builder.add_node('flight1', flight1)
builder.add_node('flight2', flight2)
builder.add_node('join', join)
builder.add_conditional_edges(START, route_test, ['flight1', 'flight2'])
builder.add_edge('flight1', 'join')
builder.add_edge('flight2', 'join')
graph = builder.compile()

print('Invoking LangGraph test...')
try:
    result = graph.invoke({'messages': ['start'], 'flight_results': [], 'next': 'route'})
    print(f'Graph result: messages={result.get("messages")}')
    for fr in result.get('flight_results', []):
        print(f'  {fr["node"]}: status={fr["result"].get("status")}')
        if fr['result'].get('status') == 'error':
            err = fr['result'].get('error', '')
            if isinstance(err, str) and 'no running event loop' in err:
                print(f'    -> ASYNC ERROR FOUND in LangGraph!')
                # Check if line 200 is in the error
                if 'line 200' in err or '_run_coroutine' in err:
                    print(f'    -> Matches _run_coroutine line 200 pattern!')
            else:
                print(f'    -> Error type: {type(err).__name__ if not isinstance(err, str) else "str"}: {str(err)[:200]}')
except Exception as e:
    print(f'Graph crashed: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

print('Done')

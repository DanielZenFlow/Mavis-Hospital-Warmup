# MAvis Hospital Warmup Assignment (02285)

A **search-based AI client** for the MAvis hospital domain where agents (robots 0-9) navigate a grid to push/pull boxes (A-Z) to goal positions.

## 🚀 Quick Start

### Build and Run

```bash
# Compile (from searchclient_java/)
javac searchclient/*.java

# Run with server
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient" -g -s 500
```

### Run with Different Strategies

```bash
# BFS (Breadth-First Search)
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -bfs" -g -s 500

# DFS (Depth-First Search)
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -dfs" -g -s 500

# A* Search
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -astar" -g -s 500

# Greedy Best-First
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -greedy" -g -s 500
```

### Benchmark with Timeout (3 minutes)

```bash
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -bfs" -g -s 500 -t 180
```

## 📋 Project Overview

**Language**: Java  
**Build**: Command-line javac  
**Entry Point**: `searchclient.SearchClient`

This client communicates with a Java server via stdin/stdout protocol to solve planning problems in the MAvis hospital domain.

## 🎯 Domain Rules

### Critical Constraints
1. **Color constraint**: Agents can ONLY push/pull boxes of the **same color**
2. **Actions**: `Move(dir)`, `Push(agentDir, boxDir)`, `Pull(agentDir, boxDir)`, `NoOp`
3. **Directions**: `N` (row-1), `S` (row+1), `W` (col-1), `E` (col+1)

### Action Mechanics

**Push**: Agent moves into the box's cell (agentDir), box moves out (boxDir)
- Box must be adjacent to agent in agentDir direction
- Destination cell for box must be free
- Agent and box CANNOT swap positions

**Pull**: Agent moves away (agentDir), box follows into agent's old cell (boxDir)
- Box must be in the **opposite** direction of boxDir from agent
- Agent's destination must be free
- Agent and box CANNOT swap positions

### Multi-Agent Rules
- **Conflicts**: Two agents/boxes moving into same cell → both get NoOp
- **Joint actions are synchronous**: All agents act simultaneously per timestep
- Cell occupancy determined at the **beginning** of each joint action

### Goal Condition
Every goal cell must have the correct object on it. Extra objects can be anywhere.

## 🏗️ Architecture

```
searchclient/
├── SearchClient.java    # Entry point: parse level → search → send plan
├── State.java           # World state: positions, walls, goals, colors
│                        #   isApplicable(action) — check preconditions
│                        #   State(parent, jointAction) — result function
│                        #   getExpandedStates() — generate successors
│                        #   isGoalState() — check if goals satisfied
├── Action.java          # Enum: Move, Push, Pull, NoOp with directions
├── Color.java           # Enum of 10 colors
├── GraphSearch.java     # Graph-Search: frontier + explored set
├── Frontier.java        # Abstract frontier + implementations:
│                        #   FrontierBFS (queue)
│                        #   FrontierDFS (stack)
│                        #   FrontierBestFirst (priority queue)
├── Heuristic.java       # Abstract heuristic with:
│                        #   HeuristicAStar: f(n) = g(n) + h(n)
│                        #   HeuristicGreedy: f(n) = h(n)
└── Memory.java          # Memory usage tracking
```

## 📝 Exercise Guide

### Exercise 1: Code Familiarization
Understand the architecture and codebase.

### Exercise 2: BFS Graph-Search
Implement standard graph-search in `GraphSearch.java`:
1. Initialize frontier with initial state, create explored set (HashSet)
2. Loop until solution found or frontier empty
3. Expand states and manage explored set

### Exercise 3: DFS
Implement `FrontierDFS` using stack (LIFO) instead of queue (FIFO).

### Exercise 4: Informed Search
1. Implement `FrontierBestFirst` with PriorityQueue
2. **Goal count heuristic**: h(n) = number of unsatisfied goals
3. **Improved heuristic**: Sum of Manhattan/BFS distances to goals

### Exercise 5: Push and Pull Actions
Extend `Action.java` and `State.java`:
- Add Push and Pull action variants (12 valid pushes, 12 valid pulls)
- Implement `isApplicable` checks
- Update state transitions

### Exercise 6: Heuristics for Box Levels
Improve heuristics for box-pushing scenarios:
- Count unsatisfied box goals + agent goals
- Sum distances from boxes to matching goals
- Consider agent-to-box distances

### Exercise 7: Multi-Agent + Boxes (Groups of 4-5)
Combine agent-goal and box-goal distances with color constraints.

## 📊 Benchmark Levels

**MAPF levels** (multi-agent pathfinding, no boxes):
- MAPF00, MAPF01, MAPF02, MAPF02C, MAPF03, MAPF03C
- MAPFslidingpuzzle, MAPFreorder2

**Single-agent with boxes**:
- SAD1, SAD2, SAD3
- SAFirefly, SACrunch
- SAsoko1_n, SAsoko2_n, SAsoko3_n (n=4..128)

## 🔧 Implementation Notes

### Server-Client Protocol
1. Client sends its name (newline-terminated)
2. Server sends full level file content
3. Client sends joint actions or comments (lines starting with `#`)
4. Server responds with `true|false|...` for each action
5. Repeat until solved or shutdown

**IMPORTANT**: 
- `System.out` = server communication ONLY
- `System.err` = debugging output

### Level File Format
```
#domain
hospital
#levelname
<name>
#colors
<color>: <agent/box>, <agent/box>, ...
#initial
<grid: + for walls, 0-9 for agents, A-Z for boxes>
#goal
<grid: + for walls, A-Z/0-9 for goals>
#end
```

### Key Points
- **Explored set**: Use `HashSet<State>` with proper `hashCode()` and `equals()`
- **Memory**: Allocate max RAM with `-Xmx8g`
- **Timeout**: 3 minutes for benchmarks (`-t 180`)
- **Plan format**: `action0|action1|...|actionN` for multi-agent

## ⚠️ Common Pitfalls

- Cell occupancy checked BEFORE action execution (no swaps)
- Never print debug info to stdout (corrupts server protocol)
- Pull direction: boxDir is where box MOVES TO, not current position
- State equality must account for ALL agent AND box positions
- Greedy solutions are NOT guaranteed optimal

## 📁 Files

- **Level files**: `levels/` directory, `.lvl` extension
- **Source files**: `searchclient/` package directory
- **Server**: `server.jar` for running simulations

## 📚 Additional Resources

For complete technical details and implementation guidance, see [CLAUDE.md](CLAUDE.md).

---

**Course**: 02285 Artificial Intelligence and Multi-Agent Systems  
**Project**: MAvis Hospital Domain Warmup Assignment

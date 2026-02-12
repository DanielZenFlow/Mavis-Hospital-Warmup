# CLAUDE.md - Project Intelligence for 02285 Warmup Assignment

## Project Overview

This is a **search-based AI client** for the MAvis hospital domain. Agents (robots 0-9)
navigate a grid, push/pull boxes (A-Z) to goal positions. The client communicates with
a Java server via stdin/stdout protocol.

**Language**: Java · **Build**: Command-line javac · **Entry Point**: `searchclient.SearchClient`

## Critical Domain Rules

These rules are **non-negotiable** and must never be violated:

1. **Color constraint**: Agents can ONLY push/pull boxes of the **same color**.
2. **Actions**: `Move(dir)`, `Push(agentDir, boxDir)`, `Pull(agentDir, boxDir)`, `NoOp`.
3. **Directions**: `N` (row-1), `S` (row+1), `W` (col-1), `E` (col+1).
4. **Push mechanics**: Agent moves into the box's cell (agentDir), box moves out (boxDir).
   The box must be adjacent to the agent in the agentDir direction. The cell the box moves
   into (boxDir from box's position) must be free. Agent and box CANNOT swap positions.
5. **Pull mechanics**: Agent moves away (agentDir), box follows into agent's old cell (boxDir).
   The box must be in the **opposite** direction of boxDir from the agent. Agent's destination
   (agentDir) must be free. Agent and box CANNOT swap positions.
6. **Conflicts** (multi-agent): Two agents/boxes moving into the same cell → both get NoOp.
   Two agents trying to move the same box → both get NoOp.
7. **Joint actions are synchronous**: All agents act simultaneously per timestep.
   Cell occupancy is determined at the **beginning** of each joint action.
8. **Goal condition**: Every goal cell has the correct object on it. Extra objects can be anywhere.

## Build and Run

```bash
# Compile (from searchclient_java/)
javac searchclient/*.java

# Run with server
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient" -g -s 500

# Run with specific strategy
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -bfs" -g -s 500
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -dfs" -g -s 500
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -astar" -g -s 500
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -greedy" -g -s 500

# Timeout (3 min benchmark)
java -jar ../server.jar -l ../levels/<level>.lvl -c "java -Xmx8g searchclient.SearchClient -bfs" -g -s 500 -t 180

# Server help
java -jar server.jar -h
```

**Benchmark output**: Use "Found solution of length xxx" and the two preceding lines.
If timeout/OOM, use latest printed values (put "-" for solution length).

## Architecture

```
searchclient/
├── SearchClient.java    # Entry point: parse level from stdin → invoke search → send plan to stdout
├── State.java           # World state: agent positions, box positions, walls, goals, colors
│                        #   isApplicable(action) — checks preconditions
│                        #   State(parent, jointAction) — Result function (creates successor state)
│                        #   getExpandedStates() — generates all successor states
│                        #   isGoalState() — checks if all goals satisfied
├── Action.java          # Enum of all actions (Move, Push, Pull, NoOp) with direction params
├── Color.java           # Enum of 10 colors
├── GraphSearch.java     # Graph-Search algorithm: frontier + explored set → returns plan
├── Frontier.java        # Abstract frontier + concrete implementations:
│                        #   FrontierBFS (queue), FrontierDFS (stack), FrontierBestFirst (priority queue)
├── Heuristic.java       # Abstract heuristic with h(n), plus:
│                        #   HeuristicAStar: f(n) = g(n) + h(n)
│                        #   HeuristicGreedy: f(n) = h(n)
└── Memory.java          # Memory usage tracking
```

## Server-Client Protocol

1. Client sends its name (one line, newline-terminated).
2. Server sends the full level file content.
3. Client sends joint actions or comments (lines starting with `#`).
4. Server responds with `true|false|...` for each agent's action success.
5. Repeat 3-4 until solved or client shuts down.

**IMPORTANT**: `System.out` = server communication ONLY. Use `System.err` for debugging.

## State Representation

Key fields in `State.java`:
```
boolean[][] walls          // walls[row][col]
char[][] boxes             // boxes[row][col] = letter or '\0'
int[][] agentRows/agentCols  // indexed by agent number
Color[] agentColors        // indexed by agent number
Color[] boxColors          // indexed by letter (A=0, B=1, ...)
char[][] goals             // goals[row][col] = letter/digit or '\0'
State parent               // for plan extraction
Action[] jointAction       // action that led to this state
int g                      // path cost (depth)
```

## Level File Format

```
#domain
hospital
#levelname
<name>
#colors
<color>: <agent/box>, <agent/box>, ...
#initial
<grid using +for walls, 0-9 for agents, A-Z for boxes, space for free>
#goal
<grid using +for walls, A-Z/0-9 for goal positions, space for no goal>
#end
```

Walls must match exactly between #initial and #goal sections.

## Exercise Implementation Guide

### Exercise 1: Code Familiarization
No code changes. Understand the architecture above.

### Exercise 2: BFS Graph-Search (modify GraphSearch.java)
Implement standard Graph-Search algorithm:
1. Initialize frontier with initial state, create empty explored set (HashSet).
2. Loop: if frontier empty → return null (no solution).
3. Pop state from frontier. If goal → extract plan and return.
4. Add state to explored set.
5. For each successor: if not in frontier and not in explored → add to frontier.
Plan extraction: follow `state.parent` chain back to root, collect `jointAction` arrays.

### Exercise 3: DFS (modify Frontier.java)
Implement `FrontierDFS`: Same interface as `FrontierBFS` but uses a **stack** (LIFO)
instead of a queue (FIFO). Use `ArrayDeque` or `LinkedList` with addFirst/removeFirst.

### Exercise 4: Informed Search (modify Frontier.java + Heuristic.java)
1. Implement `FrontierBestFirst`: Use `PriorityQueue<State>` ordered by the Heuristic comparator.
2. **Goal count heuristic**: h(n) = number of goal cells not yet satisfied.
   For MAPF levels (no boxes): count agent goals where agent is not at its goal position.
3. **Improved heuristic**: Sum of Manhattan distances (or BFS-precomputed true distances)
   from each agent/box to its nearest matching goal. Consider preprocessing distances
   in the Heuristic constructor.

### Exercise 5: Push and Pull Actions (modify Action.java + State.java)
Extend `Action.java`:
- Add `Push(agentDir, boxDir)` for all 4×4 direction combinations (16 pushes, though
  some like Push(N,S) are valid — agent and box can move in different directions).
  Actually, Push(dir, oppositeDir) is invalid because the box would move into the agent's
  original cell which the agent just vacated... wait, re-read: for Push, agent moves INTO
  the box, so Push(W,E) means agent goes west (into box), box goes east — but the agent
  IS west of the box after, and box moved east... Actually Push(agentDir, boxDir) where
  boxDir = opposite(agentDir) would mean the box moves back where the agent came from,
  which is free. But the spec says the cell of β in direction boxDir must be free, and the
  agent has already moved to β's old position. Let me re-read:
  - Agent moves in agentDir → agent goes to cell where box was.
  - Box moves in boxDir → box goes from its old position in boxDir direction.
  - The cell that the box moves to must be free (checked BEFORE the action).
  - This means Push(W,E) is impossible because the agent is east of the box, moves west
    into the box's cell, and the box would need to move east into the agent's old cell — but
    cell occupancy is checked BEFORE the action, so the agent's old cell IS occupied (by agent).
  - **Result**: `boxDir` cannot equal the opposite of `agentDir`.

  Valid push combinations: agentDir × boxDir where boxDir ≠ opposite(agentDir) → 4×3 = 12 pushes.

Extend `State.java`:
- `isApplicable`: For Push, check (1) cell in agentDir from agent contains a same-color box,
  (2) cell in boxDir from that box is free. For Pull, check (1) cell in agentDir from agent
  is free, (2) cell in opposite(boxDir) from agent contains a same-color box.
- State constructor (Result function): Apply position changes for agent and box.
- `getExpandedStates`: Generate states for all applicable Move + Push + Pull + NoOp actions.

### Exercise 6: Heuristics for Box Levels (modify Heuristic.java)
1. **Goal count for boxes**: h(n) = count of unsatisfied box goals + unsatisfied agent goals.
2. **Improved heuristic ideas**:
   - Sum of Manhattan/true distances from each box to its nearest matching goal.
   - Add distance from agent to nearest unsatisfied-goal box.
   - BFS precomputation: from each goal cell, BFS ignoring boxes to get true wall-respecting
     distances. Store in a 2D distance map per goal. Look up box positions at search time.
   - For Sokoban-style levels: consider that agent must be adjacent to push, so add
     min distance from agent to any box that needs moving.

### Exercise 7: Multi-Agent + Boxes Heuristic (groups of 4-5 only)
Combine agent-goal distances and box-goal distances. Consider color constraints when
matching boxes to goals (only count boxes the right-colored agent can move).

## Benchmark Levels

**MAPF levels** (multi-agent pathfinding, no boxes):
MAPF00, MAPF01, MAPF02, MAPF02C, MAPF03, MAPF03C, MAPFslidingpuzzle, MAPFreorder2

**Single-agent with boxes**:
SAD1, SAD2, SAD3, SAFirefly, SACrunch, SAsoko1_n, SAsoko2_n, SAsoko3_n (n=4..128)

**State space analysis factors**:
- Grid free cells × number of agents = position combinations
- For MAPF: |free cells|^|agents| (agents are distinguishable)
- For box levels: |free cells|^(|agents| + |boxes|) / overlaps
- Branching factor per agent: 4 moves + 12 pushes + 12 pulls + 1 noop = 29 (max)
- Joint branching factor: (per-agent branching)^|agents|

## Key Implementation Notes

- **Explored set**: Use `HashSet<State>`. State must implement `hashCode()` and `equals()`
  correctly (already provided in the starter code).
- **Frontier membership check**: `contains(state)` must be efficient. For BFS/DFS use a
  parallel HashSet. For BestFirst, the PriorityQueue doesn't support efficient contains —
  use a parallel HashSet or accept the sub-optimality (assignment says this is acceptable).
- **Memory**: Allocate max RAM with `-Xmx`. Use `Memory.java` to monitor usage.
- **Timeout**: 3 minutes (`-t 180`). Check periodically in search loop.
- **Plan format**: Each line sent to server is `action0|action1|...|actionN` for N+1 agents.
  Single agent: just `Move(E)` etc. with no pipe separator.

## File Conventions

- **Level files**: `levels/` directory, `.lvl` extension
- **All output to server**: `System.out.println()` — never print debug info here
- **All debug output**: `System.err.println()` — this goes to terminal
- **Source files**: `searchclient/` package directory
- **Custom levels**: Create in `levels/` with the level format above

## Design Level Tips

- BFSfriendly level: Design so DFS goes deep into a dead-end branch while BFS finds
  the shallow solution quickly. Long corridor with dead end + short path to goal.
- Test levels for push/pull: Small grids (4×4) with one agent, one box, one goal.
  Verify action correctness by checking server responses (true/false).

## Common Pitfalls

- Forgetting that cell occupancy is checked BEFORE action execution (no swaps possible).
- Printing to stdout instead of stderr (corrupts server protocol).
- Not handling the case where multiple boxes have the same letter (same type, different instances).
- Pull direction confusion: boxDir is where the box MOVES TO, not where it currently is.
  The box is in the **opposite** of boxDir relative to the agent.
- State equality must account for all agent positions AND all box positions.
- For greedy best-first, solutions are NOT guaranteed optimal — this is expected.

package searchclient;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;

public class GraphSearch {

    public static Action[][] search(State initialState, Frontier frontier)
    {
        int iterations = 0;

        frontier.add(initialState);
        HashSet<State> expanded = new HashSet<>();

        while (true)
        {
            // Print a status message every 10000 iteration
            if (++iterations % 10000 == 0)
            {
                printSearchStatus(expanded, frontier);
            }

            // If frontier is empty, no solution exists
            if (frontier.isEmpty())
            {
                printSearchStatus(expanded, frontier);
                return null;
            }

            // Pop state from frontier
            State state = frontier.pop();

            // If goal state, extract and return plan
            if (state.isGoalState())
            {
                printSearchStatus(expanded, frontier);
                return state.extractPlan();
            }

            // Add state to explored set
            expanded.add(state);

            // Expand state and add successors to frontier
            for (State child : state.getExpandedStates())
            {
                if (!expanded.contains(child) && !frontier.contains(child))
                {
                    frontier.add(child);
                }
            }
        }
    }

    private static long startTime = System.nanoTime();

    private static void printSearchStatus(HashSet<State> expanded, Frontier frontier)
    {
        String statusTemplate = "#Expanded: %,8d, #Frontier: %,8d, #Generated: %,8d, Time: %3.3f s\n%s\n";
        double elapsedTime = (System.nanoTime() - startTime) / 1_000_000_000d;
        System.err.format(statusTemplate, expanded.size(), frontier.size(), expanded.size() + frontier.size(),
                          elapsedTime, Memory.stringRep());
    }
}

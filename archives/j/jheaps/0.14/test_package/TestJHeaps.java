import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

import org.jheaps.AddressableHeap;
import org.jheaps.array.BinaryArrayAddressableHeap;
import org.jheaps.monotone.DoubleRadixAddressableHeap;
import org.jheaps.tree.PairingHeap;

/**
 * End-to-end OpenHarmony consumer scenario for the packaged jheaps jar:
 * deterministic strongly-connected digraph, single-source shortest paths with
 * Dijkstra driven by three different jheaps heap families (pairing tree heap,
 * binary array addressable heap, double radix monotone heap), each
 * cross-checked against a Bellman-Ford reference computed in the consumer.
 */
public class TestJHeaps {

    private interface HeapFactory {
        AddressableHeap<Double, Integer> create(double minKey, double maxKey);
    }

    static final int NODES = 64;
    static final int MAX_WEIGHT = 97;
    static final int EXPECTED_CHECKS = 209;

    static int checks = 0;
    static int decreaseKeyUses = 0;

    private static void require(boolean condition, String what) {
        if (!condition) {
            throw new AssertionError("failed: " + what);
        }
        checks++;
    }

    private static List<List<int[]>> adjacency(List<int[]> edges) {
        List<List<int[]>> adj = new ArrayList<List<int[]>>();
        for (int u = 0; u < NODES; u++) {
            adj.add(new ArrayList<int[]>());
        }
        for (int[] e : edges) {
            adj.get(e[0]).add(new int[] { e[1], e[2] });
        }
        return adj;
    }

    private static double[] bellmanFord(List<int[]> edges) {
        double[] dist = new double[NODES];
        Arrays.fill(dist, Double.POSITIVE_INFINITY);
        dist[0] = 0.0;
        for (int round = 0; round < NODES - 1; round++) {
            boolean changed = false;
            for (int[] e : edges) {
                if (dist[e[0]] + e[2] < dist[e[1]]) {
                    dist[e[1]] = dist[e[0]] + e[2];
                    changed = true;
                }
            }
            if (!changed) {
                break;
            }
        }
        return dist;
    }

    private static double[] dijkstra(List<List<int[]>> adj, HeapFactory factory,
            long[] usage) {
        double upper = (double) (NODES - 1) * MAX_WEIGHT + 1.0;
        double[] dist = new double[NODES];
        Arrays.fill(dist, Double.POSITIVE_INFINITY);
        dist[0] = 0.0;
        AddressableHeap<Double, Integer> heap = factory.create(0.0, upper);
        @SuppressWarnings("unchecked")
        AddressableHeap.Handle<Double, Integer>[] handles =
                new AddressableHeap.Handle[NODES];
        handles[0] = heap.insert(0.0, 0);
        require(handles[0].getKey() == 0.0 && handles[0].getValue() == 0,
                "source handle key/value");
        boolean[] settled = new boolean[NODES];
        while (!heap.isEmpty()) {
            AddressableHeap.Handle<Double, Integer> min = heap.deleteMin();
            int u = min.getValue();
            settled[u] = true;
            for (int[] edge : adj.get(u)) {
                int v = edge[0];
                if (settled[v]) {
                    continue;
                }
                double candidate = dist[u] + edge[1];
                if (handles[v] == null) {
                    handles[v] = heap.insert(candidate, v);
                    dist[v] = candidate;
                } else if (candidate < dist[v]) {
                    decreaseKeyUses++;
                    handles[v].decreaseKey(candidate);
                    dist[v] = candidate;
                }
            }
        }
        usage[0] += heap.size();
        require(heap.size() == 0, "heap drained");
        boolean allSettled = true;
        boolean withinUpper = true;
        for (int v = 0; v < NODES; v++) {
            allSettled &= settled[v];
            withinUpper &= dist[v] >= 0.0 && dist[v] <= upper;
        }
        require(allSettled, "all vertices settled");
        require(withinUpper, "all distances within radix bound");
        return dist;
    }

    private static void requireSame(double[] actual, double[] expected,
            String what) {
        require(actual.length == expected.length, what + " length");
        for (int v = 0; v < expected.length; v++) {
            require(Math.abs(actual[v] - expected[v]) < 1e-9,
                    what + " distance " + v);
        }
    }

    public static void main(String[] args) {
        Random random = new Random(1L);
        List<int[]> edges = new ArrayList<int[]>();
        // Strongly connected ring: guarantees every vertex is reachable.
        for (int u = 0; u < NODES; u++) {
            int v = (u + 1) % NODES;
            edges.add(new int[] { u, v, 1 + (u * 7) % MAX_WEIGHT });
        }
        // Deterministic extra edges (dense enough to force decreaseKey).
        for (int k = 0; k < 4 * NODES; k++) {
            int u = random.nextInt(NODES);
            int v = (u + 1 + random.nextInt(NODES - 1)) % NODES;
            edges.add(new int[] { u, v, 1 + random.nextInt(MAX_WEIGHT) });
        }

        List<List<int[]>> adj = adjacency(edges);
        double[] reference = bellmanFord(edges);

        final double upper = (double) (NODES - 1) * MAX_WEIGHT + 1.0;
        HeapFactory pairing = new HeapFactory() {
            public AddressableHeap<Double, Integer> create(double minKey,
                    double maxKey) {
                return new PairingHeap<Double, Integer>();
            }
        };
        HeapFactory array = new HeapFactory() {
            public AddressableHeap<Double, Integer> create(double minKey,
                    double maxKey) {
                return new BinaryArrayAddressableHeap<Double, Integer>();
            }
        };
        HeapFactory radix = new HeapFactory() {
            public AddressableHeap<Double, Integer> create(double minKey,
                    double maxKey) {
                return new DoubleRadixAddressableHeap<Integer>(minKey, maxKey);
            }
        };

        long[] usage = new long[] { 0 };
        double[] viaPairing = dijkstra(adj, pairing, usage);
        double[] viaArray = dijkstra(adj, array, usage);
        double[] viaRadix = dijkstra(adj, radix, usage);

        requireSame(viaPairing, reference, "pairing vs bellman-ford");
        requireSame(viaArray, reference, "binary-array vs bellman-ford");
        requireSame(viaRadix, reference, "double-radix vs bellman-ford");

        require(decreaseKeyUses > 0, "decreaseKey exercised");
        require(usage[0] == 0, "all heaps fully drained");

        System.out.println("JHEAPS_OS=" + System.getProperty("os.name"));
        System.out.println("JHEAPS_JAVA=" + System.getProperty("java.version"));
        System.out.println("JHEAPS_NODES=" + NODES + " DECREASE_KEYS="
                + decreaseKeyUses);
        if (checks != EXPECTED_CHECKS) {
            throw new AssertionError("internal: checks=" + checks + " expected "
                    + EXPECTED_CHECKS);
        }
        System.out.println("jheaps 0.14 ohos dijkstra tests passed: " + checks);
    }
}

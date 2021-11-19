"""
Start a cluster with Dask Gateway, print the dashboard link, and run some tasks.
"""
import dask_gateway
from distributed import wait


def inc(x):
    return x + 1


def main():
    gateway = dask_gateway.Gateway()

    print("Starting cluster")
    cluster = gateway.new_cluster()
    client = cluster.get_client()
    print("Dashboard at:", client.dashboard_link)

    cluster.scale(2)

    futures = client.map(inc, list(range(100)))
    _ = wait(futures)

    print("Closing cluster")
    cluster.close()


if __name__ == "__main__":
    main()

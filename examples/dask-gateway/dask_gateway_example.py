import dask_gateway
from distributed import wait


def inc(x):
    return x + 1


def main():
    gateway = dask_gateway.Gateway()
    print(f"{len(gateway.list_clusters())} running clusters")

    print("starting cluster")
    cluster = gateway.new_cluster()
    client = cluster.get_client()
    print(client.dashboard_link)

    cluster.scale(2)

    futures = client.map(inc, list(range(100)))
    _ = wait(futures)

    print("closing cluster")
    cluster.close()


if __name__ == "__main__":
    main()

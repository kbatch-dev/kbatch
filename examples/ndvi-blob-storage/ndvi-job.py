"""
Make an NDVI layer from ...
"""
import io
import os
import pystac_client
import stackstac
import planetary_computer
import time

import azure.storage.blob
import rioxarray  # noqa
import matplotlib.pyplot as plt


def main():
    print("searching...")
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1"
    )
    items = catalog.search(collections=["sentinel-2-l2a"], limit=1)
    item = next(items.get_items())

    print(f"found {item.id} from {item.datetime:%Y-%m-%dT%H:%M:%S}")

    signed_item = planetary_computer.sign(item)
    ds = stackstac.stack(
        signed_item.to_dict(), assets=["B04", "B08"], resolution=200, chunksize=4096
    ).squeeze()
    red = ds.sel(band="B04")
    nir = ds.sel(band="B08")

    print("computing ndvi...")
    t0 = time.time()
    ndvi = ((nir - red) / (red + nir)).compute()
    t1 = time.time()
    print(f"computed ndvi in {t1 - t0:0.2f}s")

    container_client = azure.storage.blob.ContainerClient(
        "https://kbatchtest.blob.core.windows.net",
        "kbatch",
        credential=os.environ["SAS_TOKEN"],
    )
    print("Creating png")
    fig, ax = plt.subplots(figsize=(12, 12))

    ndvi.plot.imshow(cmap="viridis", vmin=-0.6, vmax=0.6, add_colorbar=False, ax=ax)
    ax.set_axis_off()

    img = io.BytesIO()
    fig.savefig(img)
    img.seek(0)

    container_client.upload_blob(f"output/ndvi/{item.id}/image.png", img)

    print("creating tif")
    ndvi.rio.to_raster("ndvi.tif", driver="COG")
    with open("ndvi.tif", "rb") as f:
        container_client.upload_blob(f"output/ndvi/{item.id}/image.tif", f)

    print("finished")


if __name__ == "__main__":
    main()

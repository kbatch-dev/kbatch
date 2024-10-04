"""
Compute NDVI for the latest Sentinel-2 image, saving to Blob Storage.
"""

import io
import os

import azure.storage.blob
import matplotlib.pyplot as plt
import planetary_computer
import pystac_client
import rioxarray  # noqa
import stackstac


def main():
    print("Starting job")
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1"
    )
    items = catalog.search(
        collections=["sentinel-2-l2a"], limit=1, query={"eo:cloud_cover": {"lt": 10}}
    )
    item = next(items.get_items())

    signed_item = planetary_computer.sign(item)
    ds = stackstac.stack(
        signed_item.to_dict(), assets=["B04", "B08"], resolution=200, chunksize=4096
    ).squeeze()
    red = ds.sel(band="B04")
    nir = ds.sel(band="B08")

    print("computing ndvi...")
    ndvi = ((nir - red) / (red + nir)).compute()

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

    container_client.upload_blob(
        f"output/ndvi/{item.id}/image.png", img, overwrite=True
    )

    print("creating tif")
    ndvi.rio.to_raster("ndvi.tif", driver="COG")
    with open("ndvi.tif", "rb") as f:
        container_client.upload_blob(
            f"output/ndvi/{item.id}/image.tif", f, overwrite=True
        )

    print("finished")


if __name__ == "__main__":
    main()

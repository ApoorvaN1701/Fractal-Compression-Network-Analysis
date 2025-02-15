# -*- coding: utf-8 -*-
"""Fractalimagecompression.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1VHvvCOZeVY42dgmseHhZ3iaWZEuNTTt6
"""

import numpy as np
import matplotlib.pyplot as plt
from skimage import io, transform
from skimage.metrics import structural_similarity as ssim
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import networkx as nx
from skimage.transform import rescale, rotate

# Define the maximum block size for Quadtree decomposition
MAX_BLOCK_SIZE = 8

def downsample_image(image, downsample_factor):
    """ Downsample the image by the provided factor. """
    return transform.resize(image, (image.shape[0] // downsample_factor, image.shape[1] // downsample_factor),
                            anti_aliasing=True)

def split_image(image, size):
    """Split the image into tiles of the specified size."""
    rows, cols = image.shape
    return [image[x:x+size, y:y+size] for x in range(0, rows, size) for y in range(0, cols, size)]

def find_best_match(tile, image):
    best_scale = 1
    best_rotation = 0
    best_i = 0
    best_j = 0
    min_diff = float('inf')

    for scale in [0.5, 1, 2]:  # Example scales
        for rotation in [0, 90, 180, 270]:  # Example rotations
            scaled_tile = rescale(tile, scale, anti_aliasing=True)
            rotated_tile = rotate(scaled_tile, rotation)
            if rotated_tile.shape[0] > image.shape[0] or rotated_tile.shape[1] > image.shape[1]:
                continue

            for i in range(image.shape[0] - rotated_tile.shape[0] + 1):
                for j in range(image.shape[1] - rotated_tile.shape[1] + 1):
                    region = image[i:i+rotated_tile.shape[0], j:j+rotated_tile.shape[1]]
                    diff = np.sum(np.abs(rotated_tile - region))
                    if diff < min_diff:
                        min_diff = diff
                        best_scale = scale
                        best_rotation = rotation
                        best_i = i
                        best_j = j

    return (best_i, best_j), best_scale, best_rotation

def fractal_compress(image, size=16):
    tiles = split_image(image, size)
    compressed_data = []
    for tile in tiles:
        match_data = find_best_match(tile, image)
        compressed_data.append(match_data)
    return compressed_data

def fractal_decompress(compressed_data, size, original_shape, original_image):
    decompressed_image = np.zeros(original_shape)
    for (i, j), scale, rotation in compressed_data:
        # Fetch the correctly transformed region from the original_image
        region = original_image[i:i+size, j:j+size]
        transformed_region = rotate(rescale(region, 1/scale, anti_aliasing=True), -rotation)
        # Place the transformed region back into the correct position
        decompressed_image[i:i+size, j:j+size] = transformed_region
    return decompressed_image

def resize_tile(tile, size):
    """Resize the compressed tile to match the original tile size."""
    return cv2.resize(tile, (size, size), interpolation=cv2.INTER_LINEAR)

def calculate_similarity(block1, block2, method):
    """Calculate the similarity between two image blocks."""
    if method == 'mse':
        block2_resized = cv2.resize(block2, (block1.shape[1], block1.shape[0]), interpolation=cv2.INTER_LINEAR)
        mse = np.mean((block1.astype(float) - block2_resized.astype(float)) ** 2)
        similarity = 1 / (1 + mse)  # Normalize similarity to range [0, 1]
    elif method == 'ssim':
        data_range = block1.max() - block1.min()
        similarity = ssim(block1, block2, data_range=data_range)
    elif method == 'cosine':
        block1_flat = block1.flatten().reshape(1, -1)
        block2_flat = block2.flatten().reshape(1, -1)
        similarity = cosine_similarity(block1_flat, block2_flat)[0][0]
    else:
        raise ValueError("Invalid similarity method. Choose from 'mse', 'ssim', 'cosine'.")
    return similarity

def construct_network(blocks, threshold, method):
    """Construct a network from compressed image data."""
    G = nx.Graph()
    num_blocks = len(blocks)
    for i in range(num_blocks):
        G.add_node(i)
    for i in range(num_blocks):
        for j in range(i + 1, num_blocks):
            similarity = calculate_similarity(blocks[i], blocks[j], method=method)
            if similarity >= threshold:
                G.add_edge(i, j, weight=similarity)
    return G

def visualize_network(G, blocks, method='mse', title="Network Visualization"):
    """Visualize the network using a simple interface."""
    pos = nx.spring_layout(G)  # Use spring layout for node positioning
    edge_weights = np.array([G[u][v]['weight'] for u, v in G.edges()])
    if edge_weights.size > 0:
        edge_weights = (edge_weights - edge_weights.min()) / (edge_weights.max() - edge_weights.min()) * 10
        nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.5)
    else:
        print("No edges to visualize.")
    nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=50)
    plt.title(f"{title} ({method})")
    plt.axis('off')  # Hide the axes
    plt.show()

def calculate_psnr(original_image, decompressed_image):
    max_pixel = 255.0 if original_image.dtype == np.uint8 else 1.0
    mse = np.mean((original_image - decompressed_image) ** 2)
    if mse == 0:
        return float('inf')  # Perfect match, no noise in signal.
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr

# Load and preprocess the image
image_path = "/content/boy.png"
image = io.imread(image_path, as_gray=True)
downsample_factor = 3
image_downsampled = downsample_image(image, downsample_factor)
compressed_tiles = fractal_compress(image_downsampled)
decompressed_image = fractal_decompress(compressed_tiles, size=16, original_shape=image_downsampled.shape, original_image=image_downsampled)
psnr_value = calculate_psnr(image_downsampled, decompressed_image)
print(f"PSNR between original and decompressed images: {psnr_value} dB")

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
ax[0].imshow(image_downsampled, cmap='gray')
ax[0].set_title('Downsampled Original Image')
ax[0].axis('off')
ax[1].imshow(decompressed_image, cmap='gray')
ax[1].set_title('Decompressed Image')
ax[1].axis('off')
plt.show()
threshold_mse = 0.2
threshold_ssim = 0.75
threshold_cosine = 0.9
consistent_tiles = [resize_tile(cv2.resize(image_downsampled[i:i+MAX_BLOCK_SIZE, j:j+MAX_BLOCK_SIZE], (MAX_BLOCK_SIZE, MAX_BLOCK_SIZE)), MAX_BLOCK_SIZE) for i in range(0, image_downsampled.shape[0], MAX_BLOCK_SIZE) for j in range(0, image_downsampled.shape[1], MAX_BLOCK_SIZE)]
G_mse = construct_network(consistent_tiles, threshold_mse, method='mse')
visualize_network(G_mse, consistent_tiles, method='mse', title="MSE Similarity Network")
G_ssim = construct_network(consistent_tiles, threshold_ssim, method='ssim')
visualize_network(G_ssim, consistent_tiles, method='ssim', title="SSIM Similarity Network")
G_cosine = construct_network(consistent_tiles, threshold_cosine, method='cosine')
visualize_network(G_cosine, consistent_tiles, method='cosine', title="Cosine Similarity Network")


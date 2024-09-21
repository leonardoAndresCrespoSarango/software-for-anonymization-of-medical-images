import nibabel as nib
import matplotlib.pyplot as plt
import numpy as np

nifti_file = 'C:/Users/lcres/PycharmProjects/flaskAnon/processed/Patient_18380000/bet_output/Series_5001_brain.nii.gz'


def visualize_nifti_grid(nifti_file):
    nifti_img = nib.load(nifti_file)
    nifti_data = nifti_img.get_fdata()
    num_slices = nifti_data.shape[2]

    cols = int(np.ceil(np.sqrt(num_slices)))
    rows = int(np.ceil(num_slices / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(20, 20))

    for i in range(rows * cols):
        row = i // cols
        col = i % cols
        ax = axes[row, col]

        if i < num_slices:
            ax.imshow(nifti_data[:, :, i], cmap='gray')
            ax.set_title(f'Slice {i + 1}')
        ax.axis('off')

    plt.show()


# Visualizar en cuadrícula
visualize_nifti_grid(nifti_file)

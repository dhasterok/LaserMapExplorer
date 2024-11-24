import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # Or another backend like 'Qt5Agg'
import numpy as np
from src.common.DataHandling import SampleObj

plt.ion()

def test_sample_obj(sample_id, file_path, negative_method):
    # Initialize the SampleObj with sample_id, file_path, and negative_method
    print(f"Initializing SampleObj with sample ID: {sample_id}")
    print(f"File path: {file_path}")
    print(f"Negative value handling method: {negative_method}\n")
    
    # Assuming the SampleObj takes these parameters during initialization
    sample_data = SampleObj(sample_id, file_path, negative_method)
    
    # Print initial data (assuming there's a method to access raw data)
    print("Initial data after loading:")
    print(sample_data.processed_data.head() if hasattr(sample_data.processed_data, 'head') else sample_data.processed_data[:10])
    
    # Plot a selected analyte column by reshaping using 'X' and 'Y'
    analyte_column = 'Al27'  # Replace with actual analyte column name
    print(f"\nVisualizing unadjusted analyte column ({analyte_column}):")
    plot_map(sample_data, analyte_column)
    
    # # Apply the negative value transformation
    # print("\nApplying negative value transformation:")
    # sample_data.apply_negative_transform()
    # print("Data after negative transformation:")
    # print(sample_data.processed_data[:10])
    
    # # Plot the data after negative transformation
    # print(f"\nVisualizing transformed analyte column ({analyte_column}):")
    # plot_map(sample_data, analyte_column)

    # # Apply robust outlier detection
    # print("\nApplying robust outlier detection:")
    # sample_data.robust_outlier_detection(
    #     lq=0.0005, 
    #     uq=99.5, 
    #     d_lq=9.95, 
    #     d_uq=99, 
    #     compositional=True, 
    #     max_val=1e6, 
    #     n_clusters=2, 
    #     shift_percentile=90
    # )
    # print("Data after outlier detection:")
    # print(sample_data.processed_data[:10])
    
    # Plot the data after outlier detection
    print(f"\nVisualizing outlier-detected analyte column ({analyte_column}):")
    plot_map(sample_data, analyte_column)

    # Final summary statistics
    print("\nFinal Data Summary:")
    print(f"Mean: {np.mean(sample_data.processed_data[analyte_column])}")
    print(f"Median: {np.median(sample_data.processed_data[analyte_column])}")
    print(f"Min: {np.min(sample_data.processed_data[analyte_column])}")
    print(f"Max: {np.max(sample_data.processed_data[analyte_column])}")

def plot_map(sample_data, analyte_column):
    # Reshape using 'X' and 'Y' dimensions
    x_unique = sample_data.processed_data['X'].nunique()
    y_unique = sample_data.processed_data['Y'].nunique()

    reshaped_array = np.reshape(
        sample_data.processed_data[analyte_column].values, 
        (y_unique, x_unique), 
        order='F'
    )
    
    plt.figure()
    plt.title(f'{analyte_column} Data Reshaped')
    plt.imshow(reshaped_array, cmap='viridis', aspect='auto')
    plt.colorbar()
    plt.show(block=True)  # Force the figure to display

if __name__ == "__main__":
    # Define sample test inputs
    sample_id = 'RM02'
    file_path = '/Users/dhasterok/maps/processed data/RM02.lame.csv'  # Replace with actual file path
    negative_method = 'gradual shift'  # Specify negative value handling method

    # Run the test on the SampleObj class
    test_sample_obj(sample_id, file_path, negative_method)

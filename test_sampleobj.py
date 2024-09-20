import matplotlib.pyplot as plt
import numpy as np
from src.DataHandling import SampleObj

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
    
    # Plot the initial data (assuming it can be visualized as an array)
    if isinstance(sample_data.processed_data, np.ndarray):
        plt.figure()
        plt.title('Initial Data Visualization')
        plt.imshow(sample_data.processed_data, cmap='viridis', aspect='auto')
        plt.colorbar()
        plt.show()

    # Apply the negative value transformation
    print("\nApplying negative value transformation:")
    sample_data.apply_negative_transform()
    print("Data after negative transformation:")
    print(sample_data.processed_data[:10])
    
    # Plot the data after negative transformation
    plt.figure()
    plt.title('Data After Negative Transformation')
    plt.imshow(sample_data.data, cmap='plasma', aspect='auto')
    plt.colorbar()
    plt.show()

    # Apply outlier detection
    print("\nApplying robust outlier detection:")
    sample_data.apply_outlier_detection()
    print("Data after outlier detection:")
    print(sample_data.data[:10])
    
    # Plot the data after outlier detection
    plt.figure()
    plt.title('Data After Outlier Detection')
    plt.imshow(sample_data.data, cmap='inferno', aspect='auto')
    plt.colorbar()
    plt.show()

    # Final summary statistics
    print("\nFinal Data Summary:")
    print(f"Mean: {np.mean(sample_data.data)}")
    print(f"Median: {np.median(sample_data.data)}")
    print(f"Min: {np.min(sample_data.data)}")
    print(f"Max: {np.max(sample_data.data)}")

if __name__ == "__main__":
    # Define sample test inputs
    sample_id = 'RM02'
    file_path = '/Users/dhasterok/maps/processed data/RM02.lame.csv'  # Replace with actual file path
    negative_method = 'gradual shift'  # Specify negative value handling method

    # Run the test on the SampleObj class
    test_sample_obj(sample_id, file_path, negative_method)

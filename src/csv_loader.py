import logging
import os
import csv # Import the csv module

# --- Logging Setup ---
# Create the logs directory if it doesn't exist
log_dir = "rebate_agent_logs"  # Name of the subdirectory
logging.basicConfig(filename=os.path.join(log_dir, 'csv_loader.log'),
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# --- CSV Setup ---
def load_csv(csv_filepath, column_index=0, convert_to_lower=True): # Add parameter, default to 0
    """Reads a CSV file and returns a set data dependent on the column."""
    dataset = set()
    header_name = f"column {column_index}"
    try:
        with open(csv_filepath, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            # Skip header row if it exists
            try:
                 next(reader, None)
            except StopIteration:
                 # Handle case where file is empty or only has header
                 pass
            for row in reader:
                # Check if row has enough columns and the specified column is not empty
                if row and len(row) > column_index and row[column_index]:
                    datapoint = row[column_index].strip() # <-- Use column_index, remove trailing whitespace
                    if convert_to_lower:
                        datapoint = datapoint.lower()  # Convert to lowercase if requested
                    dataset.add(datapoint)  # Add to the set
        logging.info(f"Successfully loaded {len(dataset)} unique values from the '{header_name}' column in this CSV: {csv_filepath}.")
        print(f"Successfully loaded {len(dataset)} unique values from the '{header_name}' column in this CSV: {csv_filepath}.")
    except FileNotFoundError:
        logging.error(f"CSV file not found at {csv_filepath}")
        print(f"Error: CSV file not found at {csv_filepath}")
    except IndexError:
         logging.error(f"Error: Column index {column_index} is out of bounds for some rows in {csv_filepath}")
         print(f"Error: Column index {column_index} is out of bounds for some rows in {csv_filepath}")
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_filepath}: {e}")
        print(f"Error reading CSV file {csv_filepath}: {e}")
    return dataset


def load_full_csv_with_headers(csv_filepath, encoding='utf-8'):
    """
    Reads a CSV file, using the first row as headers, and returns a list of dictionaries.

    Args:
        csv_filepath (str): The path to the CSV file.
        encoding (str, optional): The encoding of the CSV file. Defaults to 'utf-8'.

    Returns:
        list[dict]: A list where each element is a dictionary representing a row.
                    Keys are taken from the CSV header row. Returns an empty list
                    if the file is not found, empty, or an error occurs.
    """
    data_list = []
    try:
        # Use csv.DictReader which automatically uses the first row as headers
        with open(csv_filepath, mode='r', newline='', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            # The DictReader iterates over rows, returning each as a dictionary
            for row in reader:
                # Optional: Clean up keys (remove leading/trailing whitespace if needed)
                cleaned_row = {k.strip(): v for k, v in row.items()}
                data_list.append(cleaned_row)

        logging.info(f"Successfully loaded {len(data_list)} rows from CSV: {csv_filepath}.")
        print(f"Successfully loaded {len(data_list)} rows from CSV: {csv_filepath}.")
        return data_list

    except FileNotFoundError:
        logging.error(f"CSV file not found at {csv_filepath}")
        print(f"Error: CSV file not found at {csv_filepath}")
        return []
    except Exception as e:
        # Catch other potential errors during reading (e.g., malformed CSV)
        logging.error(f"Error reading CSV file {csv_filepath}: {e}")
        print(f"Error reading CSV file {csv_filepath}: {e}")
        return []
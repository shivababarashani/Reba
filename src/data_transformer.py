import re
import logging
import os

# --- Logging Setup ---
# Create the logs directory if it doesn't exist
log_dir = "rebate_agent_logs"  # Name of the subdirectory
logging.basicConfig(filename=os.path.join(log_dir, 'data_transform.log'),
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def transform_extracted_data(raw_data):
    """
    Transforms and cleans the raw extracted data dictionary.
    Applies data type conversions, handles 'null' strings, and formats specific fields.
    Returns the cleaned and transformed dictionary.
    """
    print("Attempting to transforming the data")
    if not raw_data:
        logging.warning("No raw data provided for transformation.")
        print("No raw data provided")
        return {}

    transformed_data = {}
    raw_data_lower_keys = {k.lower(): v for k, v in raw_data.items()} # Normalize keys immediately

    # Define expected fields to ensure we process them all
    expected_fields = [
        "manufacturer_product_code", "product_id", "product_name", "subsidiary",
        "start_date", "end_date", "campaign_promotion_related", "rebate_compensation_factor",
        "max_spq",
    ]

    for field in expected_fields:
        raw_value = raw_data_lower_keys.get(field, None) # Use lower key for lookup

        # Handle 'null' string case first for all fields
        if isinstance(raw_value, str) and raw_value.strip().lower() == "null":
            transformed_data[field] = None
            continue # Move to the next field

        # --- Apply transformations based on field ---
        if field == "subsidiary":
            # Map to "NL", "BE", "DE" or None
            if isinstance(raw_value, str):
                upper_value = raw_value.strip().upper()
                if upper_value in ["NL", "BE", "DE", "NETHERLANDS", "BELGIUM", "GERMANY", "NEDERLAND", "BELGIE", "Duitsland"]: # Add common variations
                     # Simple mapping - you might need more sophisticated logic here
                    if "NETHERLANDS" in upper_value or "NL" in upper_value:
                         transformed_data[field] = "NL"
                    elif "BELGIUM" in upper_value or "BE" in upper_value:
                         transformed_data[field] = "BE"
                    elif "GERMANY" in upper_value or "DE" in upper_value:
                         transformed_data[field] = "DE"
                    else:
                         transformed_data[field] = None # Fallback if string not clearly one of them
                else:
                     transformed_data[field] = None # Not recognized subsidiary
            else:
                transformed_data[field] = None # Not a string

        elif field == "rebate_compensation_factor":
            # Attempt to extract a float number from the string
            transformed_value = None
            if isinstance(raw_value, str):
                # Use regex to find potential numbers (integers or floats)
                match = re.search(r'(\d+(\.\d+)?([,\.]\d+)?)', raw_value.replace(',', '.')) # Replace comma decimal with dot
                if match:
                    try:
                        # Take the first found number and convert
                        transformed_value = float(match.group(1))
                    except (ValueError, TypeError):
                        logging.warning(f"Could not convert extracted number '{match.group(1)}' for {field} to float: {raw_value}")
                        transformed_value = None
                else:
                    logging.info(f"No number found for {field} in raw value: {raw_value}. Setting to None.")
                    transformed_value = None # No number found
            elif isinstance(raw_value, (int, float)):
                 transformed_value = float(raw_value) # Already a number, just cast to float
            else:
                 logging.warning(f"Unexpected raw value type for {field}: {raw_value}. Setting to None.")
                 transformed_value = None # Not a string or number

            transformed_data[field] = transformed_value


        elif field == "max_spq":
            # Attempt to extract an integer number from the string
            transformed_value = None
            if isinstance(raw_value, str):
                 # Look for digits at the start or within the string
                match = re.search(r'\d+', raw_value)
                if match:
                    try:
                        transformed_value = int(match.group(0))
                    except (ValueError, TypeError):
                        logging.warning(f"Could not convert extracted number '{match.group(0)}' for {field} to int: {raw_value}")
                        transformed_value = None
                else:
                     logging.info(f"No integer found for {field} in raw value: {raw_value}. Setting to None.")
                     transformed_value = None # No integer found
            elif isinstance(raw_value, int):
                 transformed_value = raw_value # Already an integer
            else:
                 logging.warning(f"Unexpected raw value type for {field}: {raw_value}. Setting to None.")
                 transformed_value = None

            transformed_data[field] = transformed_value

        # For all other fields, ensure they are strings or None
        else:
            if isinstance(raw_value, (str, int, float, bool)):
                transformed_data[field] = str(raw_value).strip() # Convert to string and strip
            elif raw_value is None:
                 transformed_data[field] = None
            else:
                logging.warning(f"Unexpected raw value type for {field}: {raw_value}. Setting to None.")
                transformed_data[field] = None

    logging.info("Finished transforming extracted data.")
    print(f"Transformed the data into: {transformed_data}") # Debugging
    return transformed_data


def transform_extracted_data_list(list_of_raw_data_items): # New signature expecting a list
    """
    Transforms and cleans a list of raw extracted data dictionaries (rebate items).
    Applies data type conversions, handles 'null' strings, formats specific fields,
    and normalizes keys for each item in the list.

    Args:
        list_of_raw_data_items (list): A list of dictionaries, where each dictionary
                                       represents a raw rebate item extracted by the LLM.

    Returns:
        list: A list of cleaned and transformed dictionaries. Returns an empty list
              if the input is not a list or is empty.
    """
    # Define expected fields to ensure we process them all
    expected_fields = [
        "manufacturer_product_code", "product_id", "product_name", "subsidiary",
        "start_date", "end_date", "campaign_promotion_related", "rebate_compensation_factor",
        "max_spq",
    ]
    transformed_items_list = []
    logging.info("Attempting to transforming the data.")
    print("Attempting to transforming the data.")

    if not isinstance(list_of_raw_data_items, list):
        logging.error(f"Input to transform_extracted_data is not a list (type: {type(list_of_raw_data_items)}). Cannot transform.")
        print(f"Error: Input to transform_extracted_data is not a list.")
        return [] # Return empty list if input is invalid

    if not list_of_raw_data_items:
        logging.info("No items provided for transformation.")
        print("No items provided for transformation.")
        return [] # Return empty list if input is empty


    # --- Iterate through each raw item in the input list ---
    for index, raw_item in enumerate(list_of_raw_data_items):
        logging.debug(f"Processing item {index} for transformation: {raw_item}")
        print(f"Processing item {index + 1}/{len(list_of_raw_data_items)} for transformation...")

        # Ensure the current item is a dictionary before processing
        if not isinstance(raw_item, dict):
            logging.warning(f"Item at index {index} is not a dictionary (type: {type(raw_item)}). Skipping transformation for this item.")
            print(f"Warning: Item {index + 1} is not a dictionary. Skipping.")
            continue # Skip this item if it's not a dictionary


        # Apply the key lowercasing to the *current item* dictionary
        try:
            raw_item_lower_keys = {k.lower(): v for k, v in raw_item.items()}
        except AttributeError:
             logging.error(f"Item at index {index} does not have an .items() method (not a dict?). Skipping.")
             print(f"Error: Item {index + 1} does not appear to be a dictionary. Skipping.")
             continue


        transformed_item = {} # This dictionary will hold the transformed data for the current item

        # --- Apply transformations based on field for the *current item* ---
        for field in expected_fields:
            raw_value = raw_item_lower_keys.get(field, None) # Use lower key for lookup in the current item

            # Handle 'null' string case first for all fields
            if isinstance(raw_value, str) and raw_value.strip().lower() == "null":
                transformed_item[field] = None # Assign to the current transformed_item
                continue # Move to the next field for this item

            # --- Apply transformations based on field type/role ---
            if field == "subsidiary":
                transformed_value = None
                if isinstance(raw_value, str):
                    upper_value = raw_value.strip().upper()
                    # Improved mapping logic
                    if "NL" in upper_value or "NETHERLANDS" in upper_value or "NEDERLAND" in upper_value:
                         transformed_value = "NL"
                    elif "BE" in upper_value or "BELGIUM" in upper_value or "BELGIE" in upper_value:
                         transformed_value = "BE"
                    elif "DE" in upper_value or "GERMANY" in upper_value or "DUITSLAND" in upper_value: # Added Duitsland
                         transformed_value = "DE"
                    # else: transformed_value remains None if not clearly matched
                # else: transformed_value remains None if not a string

                transformed_item[field] = transformed_value # Assign to the current transformed_item


            elif field == "rebate_compensation_factor":
                transformed_value = None
                if isinstance(raw_value, str):
                    # Use regex to find potential numbers (integers or floats)
                    # Look for numbers possibly with currency symbols (€, EUR, $) or percentage (%)
                    # Be careful not to capture percentage sign as part of the number if it means '% of price'
                    # The prompt asks for ABSOLUTE numerical factor, so ignore %
                    match = re.search(r'[€$]?\s*(\d+(\.\d+)?([,\.]\d+)?)\s*(EUR)?', raw_value.replace(',', '.'), re.IGNORECASE) # Replace comma decimal with dot
                    if match:
                        try:
                            # Take the first found number part and convert
                            # match.group(1) captures the main number part (e.g., "5.5", "10", "10,50")
                            transformed_value = float(match.group(1))
                            # Check if it looks like a percentage *after* getting the number (heuristic)
                            if '%' in raw_value and transformed_value > 1: # If % is present and number > 1, it's probably percentage
                                logging.info(f"Raw value '{raw_value}' for {field} looks like a percentage. Setting to None as only absolute factor is required.")
                                transformed_value = None # Not an absolute factor if it seems like a percentage
                            elif transformed_value <= 0: # Factors must be positive
                                logging.warning(f"Extracted factor '{transformed_value}' for {field} is not > 0. Setting to None.")
                                transformed_value = None

                        except (ValueError, TypeError):
                            logging.warning(f"Could not convert extracted number '{match.group(1)}' for {field} to float from raw value: '{raw_value}'. Setting to None.")
                            transformed_value = None
                    else:
                        logging.info(f"No clear absolute number found for {field} in raw value: '{raw_value}'. Setting to None.")
                        # transformed_value remains None

                elif isinstance(raw_value, (int, float)):
                     transformed_value = float(raw_value) # Already a number, just cast to float and keep

                # else: transformed_value remains None if not a string or number

                transformed_item[field] = transformed_value # Assign to the current transformed_item


            elif field == "max_spq":
                transformed_value = None
                if isinstance(raw_value, str):
                     # Look for digits at the start or within the string
                    match = re.search(r'\d+', raw_value)
                    if match:
                        try:
                            # Take the first sequence of digits
                            transformed_value = int(match.group(0))
                        except (ValueError, TypeError):
                            logging.warning(f"Could not convert extracted number '{match.group(0)}' for {field} to int from raw value: '{raw_value}'. Setting to None.")
                            transformed_value = None
                    # else: transformed_value remains None if no integer found
                elif isinstance(raw_value, int):
                     transformed_value = raw_value # Already an integer and keep
                # else: transformed_value remains None if not a string or int


                transformed_item[field] = transformed_value # Assign to the current transformed_item

            # For all other fields (product codes, names, dates, boolean), ensure they are strings or None
            # Dates are expected in YYYY-MM-DD by validation, but LLM might give other strings.
            # The transformer ensures they are strings if not None, validation checks the format.
            elif field in ["manufacturer_product_code", "product_id", "product_name", "start_date", "end_date"]:
                if isinstance(raw_value, (str, int, float, bool)):
                    transformed_item[field] = str(raw_value).strip() # Convert to string and strip
                elif raw_value is None:
                     transformed_item[field] = None
                else:
                    logging.warning(f"Unexpected raw value type for {field}: {raw_value}. Setting to None.")
                    transformed_item[field] = None

            # Handle boolean field campaign_promotion_related
            elif field == "campaign_promotion_related":
                 # LLM should return true/false JSON boolean. Ensure it remains a boolean or is None.
                 if isinstance(raw_value, bool) or raw_value is None:
                     transformed_item[field] = raw_value
                 elif isinstance(raw_value, str):
                     # Simple string to boolean conversion if LLM didn't use JSON boolean
                     lower_value = raw_value.strip().lower()
                     if lower_value in ["true", "yes", "1"]:
                          transformed_item[field] = True
                     elif lower_value in ["false", "no", "0"]:
                          transformed_item[field] = False
                     else:
                         logging.warning(f"Cannot convert string '{raw_value}' for {field} to boolean. Setting to None.")
                         transformed_item[field] = None
                 else:
                    logging.warning(f"Unexpected raw value type for boolean field {field}: {raw_value}. Setting to None.")
                    transformed_item[field] = None


        # After processing all fields for the current item, append it to the list
        transformed_items_list.append(transformed_item)
        logging.debug(f"Item {index + 1} transformed: {transformed_item}")

    # --- End of item iteration ---

    logging.info(f"Finished data transformation. Transformed {len(transformed_items_list)} items.")
    print(f"Finished data transformation. Transformed {len(transformed_items_list)} items.")
    # print(f"Transformed data list: {transformed_items_list}") # Might be too verbose for console

    return transformed_items_list

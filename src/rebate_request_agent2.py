from dotenv import load_dotenv
import re
import logging
import openai
import json  # For parsing JSON from LLM
import os
import email_extractor
import csv_loader
import data_transformer
import mock_emails_data
from datetime import datetime

# --- OpenAI Setup ---
load_dotenv(dotenv_path=".env")
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Logging Setup ---
# Create the logs directory if it doesn't exist
log_dir = "rebate_agent_logs"  # Name of the subdirectory
logging.basicConfig(filename=os.path.join(log_dir, 'rebate_agent.log'),
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def is_valid_rebate_request(email, confidence_threshold=0.85):
    """Determines if an email is a valid rebate request using an LLM."""
    rebate_definition = """
    Hereby the definition of a rebate request:
    In this context, it's about us, the company or emailaddress, receiving a proposal for a discount on 1 or more products from the vendor.
    Note that we should be given the discount, e.g. it's not that we're going to pay someone, the vendor has to pay us.
    
    This discount can be given in 2 different ways:
    1) Our sales during the period of the rebate. This is called a sell-out rebate.
    2) Our purchase orders from the Vendor during the period of the rebate. This is called a sell-in rebate.  
    
    Only consider the first option for now. Also take into account that the proposal is sent via email from the vendor to us. 
    Not all emails are created equal, some might be more formal, some might be more casual.
    This email often contains terms like 'rebate,' 'claim,' 'refund,' or 'discount' or the Dutch translations of these words. 
    It could also reference an action period. E.g. the mail could offer a discount during a certain action period, like black friday, holiday pay or more, implying a rebate.
    The email initiated by the vendor may also reference a specific purchase, a time period, or a product category. E.g. it could mention all Televisions during christmas.
    Emails about temporary or permanent purchase price reductions, price protections, msrp's, media budgets etcetera are NOT rebate requests.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Or your preferred model
            messages=[
                {"role": "user",
                 "content": f"Is this email a rebate request? Answer 'yes' or 'no' and provide a confidence score (0-1). "
                            f"Here's the definition of a rebate request: {rebate_definition} "
                            f"Email Body: {email.body} Email Subject: {email.subject}"}
            ],
            temperature=0.2  # Lower temperature for more deterministic results
        )
        llm_response = response.choices[0].message.content
        logging.info(f"LLM Response to the question if it's a valid rebate request: {llm_response}")
        print("Asking LLM whether the email is a related to a rebate request")  # Debugging
        print(f"Response LLM: {llm_response}")  # Debugging
        if "yes" in llm_response.lower():
            logging.info("LLM determined the email is a rebate request.")
            # Extract confidence score (more robust regex)
            match = re.search(r".*?confidence\s*score:?\s*(\d+\.?\d*)", llm_response, re.IGNORECASE)
            if match:
                confidence = float(match.group(1))
                logging.info(f"Extracted confidence: {confidence}")
                if confidence >= confidence_threshold:
                    logging.info(f"Email is a valid rebate request with confidence {confidence}.")
                    logging.info("Returning True from is_valid_rebate_request")  # Added
                    print(f"LLM validated that the confidence {confidence} is higher then the threshold {confidence_threshold}")
                    print(f"Therefore the end state is considered TRUE")
                    return True
                else:
                    logging.info(f"Email is not considered a valid rebate request due to low confidence ({confidence}).")
                    print(f"LLM later decided that the confidence {confidence} is lower then the threshold {confidence_threshold}")
                    print(f"Therefore the end state is considered FALSE")
                    return False
            else:
                logging.warning(f"Could not extract confidence from LLM response: {llm_response}")
                print(f"Could not extract confidence from LLM response: {llm_response}")
                print(f"Therefore the end state is considered FALSE")
                return False  # Default to False if no confidence
        else:
            logging.info(f"LLM determined email is not a rebate request.")
            print(f"LLM determined email is not a rebate request.")
            print(f"Therefore the end state is considered FALSE")
            return False
    except openai.APIConnectionError as e:
        logging.error(f"Error connecting to OpenAI API: {e}")
        return False
    except openai.RateLimitError as e:
        logging.error(f"OpenAI Rate Limit Error: {e}")
        return False
    except openai.APIStatusError as e:
        logging.error(f"OpenAI API Status Error: {e}")
        return False


# --- LLM Data Extraction Function (Updated for multiple items) ---
def rebate_data_email_extractor(email):
    """
    Extracts relevant data for multiple rebate items from the email using an LLM,
    requesting JSON output structured as a list of items.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Or a model fine-tuned for extraction
            messages=[
                {"role": "user",
                 "content": f"""
                Extract all individual rebate items mentioned in this email and return the information as a JSON object.
                The root object MUST contain a single key named 'rebate_items'.
                The value associated with the 'rebate_items' key MUST be a JSON array.
                Each object within the 'rebate_items' array MUST represent a unique product-subsidiary combination for which a rebate is proposed.
                If no rebate items are found, the 'rebate_items' array should be empty [].
                If a specific field for an item is not found or is unclear, use 'null' for that field's value within the item's object.

                For EACH object in the 'rebate_items' array, extract the following fields:

                manufacturer_product_code: string. The unique code assigned by the manufacturer to the product, used by the vendor.
                product_id: string. The unique identifier for the product within our systems, used by us. (even though often presented as a number)
                product_name: string. The name or description of the product.
                subsidiary: string, transform to 1 of these 3 EXACTLY: ("NL", "BE", "DE"). If subsidiary is unclear or not mentioned for an item, use null.
                start_date: date string. Format as "YYYY-MM-DD". Transform descriptions like "Q3 2024" to the *start* date of Q3 2024 ("2024-07-01"). If unclear, use null.
                end_date: date string. Format as "YYYY-MM-DD". Transform descriptions like "Q3 2024" to the *end* date of Q3 2024 ("2024-09-30"). If unclear, use null.
                campaign_promotion_related: boolean. Indicates whether the rebate is associated with a specific promotional campaign (e.g., Black Friday, Holiday Pay). If unclear, use null.
                rebate_compensation_factor: float. The absolute numerical factor used to calculate the rebate amount (e.g., 5 euros becomes 5.0, €10,50 is 10.50, "10%" or "5 EUR per unit" should be represented as null if the absolute number isn't clear). If unclear or not a pure number, use null.
                max_spq: integer. Indicates whether there is a maximum quantity of products eligible for the rebate. This should be specified as a number in the email. If unclear or not specified as a number, use null.

                Example of expected JSON output structure:
                  "rebate_items": [
                      "manufacturer_product_code": "abcfg678",
                      "product_id": "1234456",
                      "product_name": "Product A",
                      "subsidiary": "NL",
                      "start_date": "2024-07-01",
                      "end_date": "2024-09-30",
                      "campaign_promotion_related": true,
                      "rebate_compensation_factor": 5.5,
                      "max_spq": 100
                    ,
                      "manufacturer_product_code": "asdf1234",
                      "product_id": "123456",
                      "product_name": "Product B",
                      "subsidiary": "BE",
                      "start_date": "2024-08-01",
                      "end_date": "2024-08-31",
                      "campaign_promotion_related": false,
                      "rebate_compensation_factor": 2.0,
                      "max_spq": null
                  ]""

                Email Body: {email.body}
                Email Subject: {email.subject}
                """}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}  # Ensure JSON output, will be an object containing the list
        )
        llm_response = response.choices[0].message.content
        logging.info(f"LLM Raw Extraction Response: {llm_response}")
        print("Asking the LLM to extract relevant data from the email")
        print(f"LLM Response: {llm_response}")

        try:
            # Attempt to parse the JSON
            raw_data = json.loads(llm_response)
            logging.info("Successfully parsed raw JSON from LLM.")

            # Expecting a root object with a 'rebate_items' key containing a list
            if isinstance(raw_data, dict) and 'rebate_items' in raw_data and isinstance(raw_data['rebate_items'], list):
                 logging.info(f"Extracted {len(raw_data['rebate_items'])} rebate items.")
                 return raw_data['rebate_items'] # Return the list of items
            else:
                 logging.error(f"LLM response did not contain the expected 'rebate_items' list structure: {llm_response}")
                 print(f"Error: LLM response did not contain the expected 'rebate_items' list structure.")
                 return [] # Return empty list if structure is wrong

        except json.JSONDecodeError:
            logging.error(f"LLM returned invalid JSON: {llm_response}")
            print(f"Error: LLM returned invalid JSON: {llm_response}")
            return []  # Return empty list to indicate failure

    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        logging.error(f"OpenAI API error during raw extraction: {e}")
        print(f"OpenAI API error during raw extraction: {e}")
        return [] # Return empty list on API errors
    except Exception as e:
        logging.error(f"An unexpected error occurred during raw extraction: {e}")
        print(f"An unexpected error occurred during raw extraction: {e}")
        return [] # Return empty list on unexpected errors

# --- Validation Function (Updated for multiple items) ---
def check_required_fields_and_validate_product_code(list_of_transformed_data_items, valid_product_codes):
    """
    Checks if required fields are present and valid for each item in a list,
    including validating the manufacturer product code against a list of valid codes.

    Args:
        list_of_transformed_data_items (list): A list of dictionaries, each representing a rebate item.
        valid_product_codes (set): A set of valid manufacturer product codes loaded from your system.

    Returns:
        list: A list of dictionaries. Each dictionary describes the validation issues
              for a single invalid item from the input list. If the returned list
              is empty, all items were valid.
              Example: [{'item_index': 0, 'issues': ['start_date', 'subsidiary']}, ...]
    """
    required_fields = [
        "start_date",
        "end_date",
        "rebate_compensation_factor",
        "subsidiary",
        "manufacturer_product_code"
    ]

    invalid_items_results = [] # List to store results for invalid items

    if not isinstance(list_of_transformed_data_items, list):
        logging.warning("Input to validation is not a list. Returning all required fields as missing for a dummy item.")
        print("Input to validation is not a list.")
        # Return a result indicating the whole input was bad, linked to index -1 or similar, or just log and return empty?
        # Let's log and return empty list, as the extractor should return a list.
        return []

    if not list_of_transformed_data_items:
         logging.info("No rebate items provided for validation.")
         print("No rebate items provided for validation.")
         return [] # No items to validate, so no invalid items

    print(f"\nStarting validation for {len(list_of_transformed_data_items)} rebate items.")

    for index, item in enumerate(list_of_transformed_data_items):
        logging.debug(f"Validating item at index {index}: {item}")
        print(f"Validating item {index + 1}/{len(list_of_transformed_data_items)}...")

        current_item_issues = [] # List to store issues for the current item

        if not isinstance(item, dict):
            current_item_issues.append(f"Item is not a dictionary (type: {type(item)})")
            logging.warning(f"Item at index {index} is not a dictionary.")
            invalid_items_results.append({"item_index": index, "issues": current_item_issues})
            continue # Skip to the next item if it's not a dict

        # Check required fields and their basic presence/format
        for field in required_fields:
            value = item.get(field)

            # Check for None or empty string (for string fields)
            # rebate_compensation_factor, max_spq can be None (null from LLM) if not found,
            # but they are *required* fields, so None means missing/unclear data.
            if value is None:
                current_item_issues.append(f"Field '{field}' is missing or null.")
                logging.debug(f"Item {index}: Field '{field}' is missing (value is None).")
                print(f"Item {index + 1}: No required data for {field} is found (value is None).")
                continue # Move to the next field check for this item

            if isinstance(value, str) and not value.strip():
                current_item_issues.append(f"Field '{field}' is empty string.")
                logging.debug(f"Item {index}: Field '{field}' is missing (value is empty string).")
                print(f"Item {index + 1}: No required data for {field} is found (value is empty string).")
                continue # Move to the next field check for this item

            # --- Specific Validation Logic for the current field ---
            if field == "subsidiary":
                # Check if subsidiary is one of the expected values ("NL", "BE", "DE")
                if not isinstance(value, str) or value not in ["NL", "BE", "DE"]:
                    current_item_issues.append(f"Field '{field}' has invalid value: '{value}'. Expected one of ('NL', 'BE', 'DE').")
                    logging.warning(f"Item {index}: Subsidiary '{value}' is not a valid subsidiary ('NL', 'BE', 'DE').")
                    print(f"Item {index + 1}: Field {field} with value '{value}' is not a valid subsidiary ('NL', 'BE', 'DE').")

            elif field == "manufacturer_product_code":
                # Check if manufacturer_product_code is a string and in the set of valid product codes
                if not isinstance(value, str) or value.strip() not in valid_product_codes:
                    current_item_issues.append(f"Field '{field}' has invalid value: '{value}'. Not found in valid product codes.")
                    logging.warning(f"Item {index}: Manufacturer product code '{value}' not found in valid product codes list.")
                    print(f"Item {index + 1}: Field {field} with value '{value}' not found in valid product codes list.")

            elif field in ["start_date", "end_date"]:
                # Check if date is a string and in "YYYY-MM-DD" format
                if not isinstance(value, str):
                    current_item_issues.append(f"Field '{field}' is not a string (type: {type(value)}). Expected YYYY-MM-DD format.")
                    logging.warning(f"Item {index}: Field '{field}' is not a string (type: {type(value)}). Expected YYYY-MM-DD format.")
                    print(f"Item {index + 1}: Field '{field}' is not a string (type: {type(value)}). Expected YYYY-MM-DD format.")
                    # No further date validation possible if not a string
                else:
                    try:
                        # *** FIX: Use datetime.strptime directly as datetime is imported as the class ***
                        datetime.strptime(value, '%Y-%m-%d')
                    except ValueError:
                        current_item_issues.append(f"Field '{field}' value '{value}' is not in expected YYYY-MM-DD format.")
                        logging.warning(f"Item {index}: Field '{field}' value '{value}' is not in expected YYYY-MM-DD format.")
                        print(f"Item {index + 1}: Field '{field}' with value '{value}' is not in expected YYYY-MM-DD format.")

            elif field == "rebate_compensation_factor":
                 # Check if it's a number (float or int) and greater than 0
                 # Note: LLM might return an integer where a float is expected, which is fine here.
                 if not isinstance(value, (int, float)):
                     current_item_issues.append(f"Field '{field}' value '{value}' is not a number (type: {type(value)}). Expected a number > 0.")
                     logging.warning(
                         f"Item {index}: Field '{field}' value '{value}' is not a number (type: {type(value)}). Expected a number > 0.")
                     print(f"Item {index + 1}: Field '{field}' value '{value}' is not a number (type: {type(value)}). Expected a number > 0.")
                 elif value <= 0:
                     current_item_issues.append(f"Field '{field}' value '{value}' is not greater than 0. Expected a number > 0.")
                     logging.warning(f"Item {index}: Field '{field}' value '{value}' is not greater than 0. Expected a number > 0.")
                     print(f"Item {index + 1}: Field '{field}' value '{value}' is not greater than 0. Expected a number > 0.")

        # After checking all fields for the current item
        if current_item_issues:
            invalid_items_results.append({"item_index": index, "issues": current_item_issues})
            logging.warning(f"Item {index}: Found issues: {', '.join(current_item_issues)}")
            print(f"Item {index + 1} validation failed with issues.")
        else:
            logging.info(f"Item {index}: All required fields found and validated.")
            print(f"Item {index + 1}: All required fields found and validated.")


    # Return the list of results for invalid items
    if invalid_items_results:
        print(f"\nValidation finished. Found issues in {len(invalid_items_results)} item(s).")
        return invalid_items_results # Return list of dictionaries describing issues
    else:
        print("\nValidation finished. All items are valid.")
        return [] # Return empty list if all items are valid


def evaluate_rebate_desirability(rebate_items_list, internal_product_data_full, mpc_header_internal, subsidiary_header_internal, required_compensation_header_internal):
    """
    Evaluates if each rebate item is 'desired' based on whether its rebate factor
    meets or exceeds the required compensation from internal data, considering the subsidiary.

    Args:
        rebate_items_list (list[dict]): A list of dictionaries representing extracted
                                         and potentially validated rebate items.
                                         Each dict must have 'manufacturer_product_code'
                                         and 'rebate_compensation_factor' and 'subsidiary'.
        internal_product_data_full (list[dict]): The full internal product data loaded
                                                  as a list of dictionaries (from load_full_csv_with_headers).
        mpc_header_internal (str): The name of the header in internal_product_data_full
                                   that contains the Manufacturer Product Code.
        subsidiary_header_internal (str): The name of the header in internal_product_data_full
                                          that contains the Subsidiary (NL, BE, DE).
        required_compensation_header_internal (str): The name of the header in
                                                     internal_product_data_full that
                                                     contains the required compensation value.

    Returns:
        list[dict]: The original rebate_items_list with an added boolean key
                    'is_desired' for each item. Items where the comparison
                    could not be made (missing data, non-numeric values,
                    MPC/Subsidiary combo not found) will have 'is_desired' set to False.
    """
    print("\n--- Evaluating Rebate Desirability (by MPC and Subsidiary) ---")
    logging.info("Starting rebate desirability evaluation (by MPC and Subsidiary).")

    # 1. Build a lookup dictionary from internal data for quick access (using (MPC, Subsidiary) as key)
    internal_lookup = {}
    if not internal_product_data_full:
        logging.warning("Internal product data is empty. Cannot evaluate desirability.")
        print("Warning: Internal product data is empty. Cannot evaluate desirability.")
    else:
        for i, row in enumerate(internal_product_data_full):
            mpc = row.get(mpc_header_internal)
            subsidiary = row.get(subsidiary_header_internal)
            required_comp_str = row.get(required_compensation_header_internal)

            # Check for required fields in internal data row
            if mpc is None or not mpc.strip():
                logging.warning(f"Internal data row {i+1}: Skipping due to missing or empty '{mpc_header_internal}'. Row: {row}")
                continue
            if subsidiary is None or not subsidiary.strip():
                logging.warning(f"Internal data row {i+1}: Skipping MPC '{mpc}' due to missing or empty '{subsidiary_header_internal}'. Row: {row}")
                continue
             # Also validate subsidiary format if needed, but for lookup, stripping is enough
             # if subsidiary.strip() not in ["NL", "BE", "DE"]:
             #     logging.warning(f"Internal data row {i+1}: Skipping MPC '{mpc}' due to invalid '{subsidiary_header_internal}' value '{subsidiary}'. Row: {row}")
             #     continue

            try:
                required_comp_float = float(required_comp_str) if required_comp_str is not None else None
                if required_comp_float is None:
                     logging.warning(f"Internal data row {i+1}: Missing or invalid '{required_compensation_header_internal}' for MPC '{mpc}' and Subsidiary '{subsidiary}'. Value was '{required_comp_str}'. Skipping lookup entry.")
                     continue # Don't add to lookup if required compensation is missing/invalid

                # Create the combined key (tuple of stripped strings)
                lookup_key = (mpc.strip().lower(), subsidiary.strip().upper()) # Standardize case for lookup
                internal_lookup[lookup_key] = required_comp_float
            except (ValueError, TypeError):
                logging.warning(f"Internal data row {i+1}: Invalid non-numeric value for '{required_compensation_header_internal}' ('{required_comp_str}') for MPC '{mpc}' and Subsidiary '{subsidiary}'. Skipping lookup entry.")
                continue # Don't add to lookup if required compensation is not a number
            except Exception as e:
                logging.error(f"Internal data row {i+1}: An unexpected error occurred building lookup for MPC '{mpc}'/Subsidiary '{subsidiary}': {e}. Skipping.")
                continue


        logging.info(f"Built internal lookup with {len(internal_lookup)} entries based on (MPC, Subsidiary).")
        print(f"Built internal lookup with {len(internal_lookup)} entries based on (MPC, Subsidiary).")


    # 2. Evaluate each rebate item from the email
    evaluated_items = []
    if not rebate_items_list:
        print("No rebate items to evaluate.")

    for i, item in enumerate(rebate_items_list):
        item_is_desired = False # Default value
        item_mpc = item.get('manufacturer_product_code')
        item_subsidiary = item.get('subsidiary')
        rebate_factor_val = item.get('rebate_compensation_factor') # Get the value as is (should be float/int or None)


        print(f"Evaluating item {i+1}/{len(rebate_items_list)} (MPC: {item_mpc}, Subsidiary: {item_subsidiary})...")
        logging.debug(f"Evaluating item {i+1}: {item}")

        # Initial checks on item data
        if item_mpc is None or not item_mpc.strip():
            logging.warning(f"Item {i}: Skipping evaluation due to missing or empty 'manufacturer_product_code'.")
            print(f"Item {i+1}: Missing Manufacturer Product Code. Not desired.")
            item['is_desired'] = False # Add flag even if skipping
            evaluated_items.append(item)
            continue
        if item_subsidiary is None or not item_subsidiary.strip():
            logging.warning(f"Item {i}: Skipping evaluation for MPC '{item_mpc}' due to missing or empty 'subsidiary'.")
            print(f"Item {i+1}: Missing Subsidiary for MPC '{item_mpc}'. Not desired.")
            item['is_desired'] = False # Add flag even if skipping
            evaluated_items.append(item)
            continue
        # Note: 'subsidiary' from extraction is already validated against ("NL", "BE", "DE")
        # by check_required_fields_and_validate_product_code, so no need for full re-validation here.

        # Create the lookup key using item data (standardize case)
        lookup_key = (item_mpc.strip().lower(), item_subsidiary.strip().upper())

        if lookup_key not in internal_lookup:
            logging.warning(f"Item {i}: Combination (MPC='{item_mpc}', Subsidiary='{item_subsidiary}') not found in internal data lookup.")
            print(f"Item {i+1}: Combination (MPC='{item_mpc}', Subsidiary='{item_subsidiary}') not found in internal data. Not desired.")
            item['is_desired'] = False # Not desired if combo not found
        else:
            required_factor = internal_lookup[lookup_key] # Get the required value (already float)
            logging.debug(f"Item {i}: Found required compensation for combo {lookup_key}: {required_factor}")
            print(f"Item {i+1}: Required compensation found ({required_factor}) for combo {lookup_key}. Comparing with rebate factor.")

            try:
                # Ensure rebate_factor from extracted data is a valid number
                # It should already be float/int from extraction/validation if valid,
                # but add robust check for None or non-numeric *after* validation.
                if rebate_factor_val is None:
                     logging.warning(f"Item {i}: 'rebate_compensation_factor' is None for combo {lookup_key}. Cannot compare.")
                     print(f"Item {i+1}: Rebate compensation factor is missing. Not desired.")
                     item_is_desired = False # Cannot be desired if factor is missing
                elif isinstance(rebate_factor_val, (int, float)):
                     rebate_factor = float(rebate_factor_val) # Already a number, just cast to float
                     # Perform the comparison
                     if rebate_factor >= required_factor:
                         item_is_desired = True
                         logging.info(f"Item {i}: Rebate ({rebate_factor}) >= required ({required_factor}) for combo {lookup_key}. Desired.")
                         print(f"Item {i+1}: Rebate {rebate_factor} >= Required {required_factor}. Desired: True.")
                     else:
                         logging.info(f"Item {i}: Rebate ({rebate_factor}) < required ({required_factor}) for combo {lookup_key}. Not desired.")
                         print(f"Item {i+1}: Rebate {rebate_factor} < Required {required_factor}. Desired: False.")
                else:
                     # This case should ideally be caught by check_required_fields_and_validate_product_code,
                     # but we handle it defensively here.
                     logging.warning(f"Item {i}: 'rebate_compensation_factor' is not a valid number ({type(rebate_factor_val)}) for combo {lookup_key}. Cannot compare.")
                     print(f"Item {i+1}: Invalid rebate compensation factor. Not desired.")
                     item_is_desired = False # Not desired if factor is invalid type


            except (ValueError, TypeError) as e:
                 # This handles errors if rebate_factor_val was, say, an empty string etc.,
                 # though check_required_fields should catch this. Defensive coding.
                logging.warning(f"Item {i}: Error converting 'rebate_compensation_factor' ('{rebate_factor_val}') to number for combo {lookup_key}: {e}. Cannot compare.")
                print(f"Item {i+1}: Error with rebate compensation factor value. Not desired.")
                item_is_desired = False
            except Exception as e:
                logging.error(f"Item {i}: An unexpected error occurred during comparison for combo {lookup_key}: {e}")
                print(f"Item {i+1}: An unexpected error occurred during comparison. Not desired.")
                item_is_desired = False


        # Add the 'is_desired' key to the item dictionary
        item['is_desired'] = item_is_desired
        evaluated_items.append(item) # Add the modified item to the new list

    print("--- Rebate Desirability Evaluation Complete ---")
    logging.info("Rebate desirability evaluation finished.")
    return evaluated_items # Return the list with the added 'is_desired' flag





# --- Test Data ---

test_email = mock_emails_data.good_email

def test_is_valid_rebate_request():
    """Tests the is_valid_rebate_request function with a draft email."""

    # Test with the good email.
    # email_extractor.get_rebate_emails()
    print("\nStarting the good_email tests\n")
    print(f"Loading email:\n{test_email}\n")
    print("Extracting some metadata from the email:")
    extracting_sender = email_extractor.get_email_metadata(test_email)
    print("\nLoading internal email database:")
    known_email_addresses = csv_loader.load_csv('Mock Data Rebate Agent - Vendors.csv', 2,False)
    print(f"These are the 2 known emails addresses: {known_email_addresses}")
    print("\nValidating whether the email is sent from a known emailaddress")
    validation_sender = email_extractor.validate_sender(extracting_sender,known_email_addresses)
    print(f"This means that the result of the email validation is: {validation_sender}")
    print("\nNext we start the validation if the email is related to an rebate request")
    is_valid_rebate_request(test_email)
    print("\nNext we extract the content of the email")
    extracting_data = rebate_data_email_extractor(test_email)
    print("\nNext we transform the extracted content of the email")
    transformed_data = data_transformer.transform_extracted_data_list(extracting_data)
    print("\nNext we load some of our internal product data so we can check whether the required data is available")
    internal_product_data = csv_loader.load_csv('Mock Data Rebate Agent - Manufacturer Product Code Data.csv', 0, False)
    print(f"This is the loaded internal data: {internal_product_data}")
    print("\nNow we're going to validate whether all required data is available.")
    validated_data = check_required_fields_and_validate_product_code(transformed_data,internal_product_data)
    print(f"Therefore the validation outcome of the required fields is: {validated_data}")
    print("\nNow we're going to evaluate the proposed rebate")
    print("First, obtain relevant internal data points")
    internal_product_data_full = csv_loader.load_full_csv_with_headers('Mock Data Rebate Agent - Internal Data.csv')
    print(f"Internal data used for checking: {internal_product_data_full}")
    print("Let's validate the desireness:")
    evaluation_outcome = evaluate_rebate_desirability(transformed_data, internal_product_data_full, "manufacturer_product_code","subsidiary", "compensation_required")
    print(f"Outcome: {evaluation_outcome}")
if __name__ == "__main__":
    test_is_valid_rebate_request()


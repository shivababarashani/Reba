import ezgmail
import logging
import os

# --- Logging Setup ---
# Create the logs directory if it doesn't exist
log_dir = "rebate_agent_logs"  # Name of the subdirectory
logging.basicConfig(filename=os.path.join(log_dir, 'email_extraction.log'),
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# --- Gmail Setup ---
def get_rebate_emails():
    """Fetches emails."""
    logging.info("Attempting to fetch emails using ezgmail.")
    try:
        # Note: '' searches all emails. You might want to refine this query later.
        emails = ezgmail.search('', maxResults=10)
        logging.info(f"Successfully fetched {len(emails)} emails.")
        logging.info(f"The emails are: {emails}")
        print(f"Successfully fetched {len(emails)} emails.")
        return emails
    except Exception as e:
        logging.error(f"Error fetching emails with ezgmail: {e}")
        print(f"Error fetching emails with ezgmail: {e}")
        return []

def get_email_metadata(email):
    """Extracts metadata from an ezgmail email object."""
    metadata = {
        "from_email": email.sender,
        "is_spam": email.isSpam,
        "labels": email.labels,
        "to_emails": email.to,  # This is a list of email addresses
        "cc_emails": email.cc,  # This is a list of email addresses
        "bcc_emails": email.bcc,  # This is a list of email addresses
        "subject": email.subject,
        "body": email.body
    }
    print(f"This is the email metadata: {metadata}")  # Debugging
    logging.info(f"Extracted metadata for email '{email.subject}': {metadata}")
    return metadata

def validate_sender(email_metadata, known_emails):
    """
    Validates if the sender's email is in the known_emails set and is not spam.
    Returns True if valid, False otherwise.
    Logs a warning if validation fails.
    """
    sender_email = email_metadata.get("from_email")
    is_spam = email_metadata.get("is_spam")

    if is_spam:
        logging.warning(f"Validation failed for email from {sender_email}: marked as spam.")
        print(f"Validation failed for email from {sender_email}: marked as spam.") # Added print for immediate feedback
        return False # Return False if spam

    if sender_email not in known_emails:
        logging.warning(f"Validation failed for email from {sender_email}: emailaddress is not known.")
        print(f"Validation failed for email from {sender_email}: emailaddress is not known.") # Added print for immediate feedback
        return False # Return False if sender is not known

    logging.info(f"Sender email '{sender_email}' is known and not spam.")
    print(f"Sender email '{sender_email}' is known and not spam.") # Added print for immediate feedback
    return True # Return True if validation passes


# Thread setup
def get_email_thread(email):
    """
    Retrieves the entire email thread associated with a given email message.

    Args:
        email (ezgmail.EmailMessage): An individual email message object that is part of a thread.

    Returns:
        ezgmail.GmailThread or None: The associated email thread object, or None if an error occurs
                                     or the email object doesn't have a thread attribute.
    """
    if not isinstance(email, ezgmail.EmailMessage):
        logging.error("Invalid input for get_email_thread: not an ezgmail.EmailMessage object.")
        print("Error: Invalid input for get_email_thread.")
        return None

    try:
        # ezgmail.EmailMessage objects have a 'thread' attribute
        email_thread = email.thread
        # Check if the retrieved thread object is indeed a GmailThread instance
        if isinstance(email_thread, ezgmail.GmailThread):
            logging.info(f"Successfully retrieved thread for email '{email.subject}' (Thread ID: {email_thread.id}).")
            print(f"Successfully retrieved thread for email '{email.subject}'.")
            return email_thread
        else:
            # This case might happen if the email object exists but its thread attribute is None
            # or not the expected type, although ezgmail usually returns GmailThread or None.
            logging.warning(f"Email '{email.subject}' does not appear to be part of a thread or thread object is not valid.")
            print(f"Warning: Email '{email.subject}' does not appear to be part of a thread.")
            return None
    except Exception as e:
        logging.error(f"Error retrieving thread for email '{email.subject}': {e}")
        print(f"Error retrieving thread for email '{email.subject}': {e}")
        return None

def extract_thread_content(thread):
    """
    Extracts content (metadata and body) from all messages within an email thread.

    Args:
        thread (ezgmail.GmailThread): An email thread object.

    Returns:
        list: A list of dictionaries, where each dictionary contains the metadata
              and body for a message in the thread. Returns an empty list if
              the input is not a valid thread object or the thread has no messages.
    """
    # Corrected type check
    if not isinstance(thread, ezgmail.GmailThread):
        logging.error("Invalid input for extract_thread_content: not an ezgmail.GmailThread object.")
        print("No Thread found")
        return []

    thread_content = []
    try:
        # ezgmail.GmailThread objects have a 'messages' attribute (a list of EmailMessage objects)
        if thread.messages:
            logging.info(f"Extracting content from {len(thread.messages)} messages in thread (Thread ID: {thread.id}).")
            print(f"Extracting content from {len(thread.messages)} messages in thread.")
            for message in thread.messages:
                # Reuse the get_email_metadata function for consistency
                message_metadata = get_email_metadata(message)
                # Add the full body of the message
                message_metadata["full_body"] = message.body # Store the full body text

                thread_content.append(message_metadata)
        else:
            logging.warning(f"Thread (ID: {thread.id}) contains no messages.")
            print(f"Warning: Thread contains no messages.")

    except Exception as e:
        logging.error(f"Error extracting content from thread (ID: {thread.id}): {e}")
        print(f"Error extracting content from thread: {e}")
        return [] # Return empty list on error

    logging.info(f"Successfully extracted content from thread (ID: {thread.id}).")
    print(f"Successfully extracted content from thread.")
    return thread_content
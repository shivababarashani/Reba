# mock_emails_data.py

class MockEmail:
    """
    A simple mock object to simulate an email message with necessary attributes.
    This class definition is placed here along with the mock data instances.
    """
    def __init__(self, subject, body, sender, isSpam=False, labels=None, to=None, cc=None, bcc=None):
        self.subject = subject
        self.body = body
        self.sender = sender
        self.isSpam = isSpam
        self.labels = labels if labels is not None else []
        self.to = to if to is not None else []
        self.cc = cc if cc is not None else []
        self.bcc = bcc if bcc is not None else []

    # Add this method to define how the object is represented as a string
    def __str__(self):
        return (f"Subject: {self.subject}\n"
                f"From: {self.sender}\n"
                f"To: {self.to}\n"
                f"Spam: {self.isSpam}\n"
                f"Body Snippet: {self.body[:1000]}...") # Show first 200 chars of body

class MockGmailThread:
    """
    A simple mock object to simulate an ezgmail.GmailThread.
    It holds a list of MockEmail objects.
    """
    def __init__(self, thread_id, messages):
        self.id = thread_id # Simulate the thread ID
        self.messages = messages # This is a list of MockEmail objects
        # Set the 'thread' attribute on each message to point back to this thread
        for message in self.messages:
            message.thread = self

    def __str__(self):
        message_subjects = [msg.subject for msg in self.messages]
        return (f"Thread ID: {self.id}\n"
                f"Messages ({len(self.messages)}): {message_subjects}")

# --- Mock Email Instances ---

good_email = MockEmail(
    subject="Iphone 16 during black friday",
    body="""
         Hey Daan,

         Ik heb een leuk verzoek voor je tijdens black friday.
         Je krijgt van mij 50 euro korting op de Iphone als je ze in de actie zet.
         Ik heb het specifiek over deze Iphone: 'dfghal908'
         De actie loopt van 2024-11-20 tot 2024-11-29.
         Dit geldt voor deze subsidiaries, NL, BE & DE.
         Maximaal 100 stuks per klant.
         """,
    sender="vendorA@example.com",
    isSpam=False,
    labels="",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"],
    bcc=[]
)

bad_email_not_rebate = MockEmail(
    subject="Price adjustment",
    body="""
         Hi Team,

         Just a quick note to inform you that the MSRP for the iPhone 16 will be permanently reduced
         by 5% starting next week. This is a standard price update, not related to any promotion.
         """,
    sender="vendorA@example.com",
    isSpam=False,
    labels="",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"],
    bcc=[]
)

bad_email_missing_data = MockEmail(
    subject="Rebate proposal",
    body="""
         Hey Daan,

         We'd like to offer a rebate on product 'xyz123'.
         """, # Missing dates, compensation factor, subsidiary
    sender="vendorA@example.com",
    isSpam=False,
    labels="",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"],
    bcc=[]
)

fraude_email = MockEmail(
    subject="Iphone 16 during black friday",
    body="""
         Hey Daan,

         Ik heb een leuke rebate voor je tijdens black friday.
         Jij geeft ons 3000 euro voor elke unit die je nu op voorraad hebt
         Ik heb het specifiek over deze Iphone: 'dfghal908'
         De actie loopt van 2024-11-20 tot 2024-11-29.
         Dit geldt voor de Benelux (Dus zowel NL en BE).
         Maximaal 100 stuks per klant.
         """,
    sender="vendorA@example.com",
    isSpam=False,
    labels="",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"],
    bcc=[]
)


# --- Mock Email Instances for Threads ---

# --- Thread 1: Successful Rebate Negotiation ---
thread1_email1 = MockEmail(
    subject="Rebate Proposal - Product X for Q3",
    body="""
Hi Daan,

Hope you're doing well.

We'd like to propose a sell-out rebate opportunity for our Product X (Manufacturer Code: PX-789) for Q3 2024.

We are offering a rebate of €7.50 per unit sold during the period of July 1st, 2024 to September 30th, 2024. This applies to sales in NL and BE.

Let us know if this is something you'd be interested in.

Best regards,

[Vendor Contact]
""",
    sender="vendorA@example.com",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"]
)

thread1_email2 = MockEmail(
    subject="RE: Rebate Proposal - Product X for Q3",
    body="""
Hi [Vendor Contact],

Thanks for the proposal!

Just a quick question regarding the maximum quantity per customer for this rebate. Is there a cap (Max SPQ)?

Also, could you confirm the exact product ID we use internally for Product X? We want to ensure we match it correctly.

Thanks!

Daan Veld
""",
    sender="daan.veld@coolblue.nl",
    to=["vendorA@example.com"],
    cc=["j.lucvanderheijden@coolblue.nl"]
)

thread1_email3 = MockEmail(
    subject="RE: Rebate Proposal - Product X for Q3",
    body="""
Hi Daan,

Thanks for getting back to us.

To clarify:
- There is **no** maximum quantity (Max SPQ) for this rebate.
- Our Product X (MPC: PX-789) corresponds to your internal Product ID: 987654.

The rebate of €7.50 per unit for NL and BE from 2024-07-01 to 2024-09-30 is confirmed.

Let us know if you have any further questions.

Best,

[Vendor Contact]
""",
    sender="vendorA@example.com",
    to=["daan.veld@coolblue.nl"],
    cc=["j.lucvanderheijden@coolblue.nl"]
)

# --- Thread 2: Invalid Request - Price Protection ---
thread2_email1 = MockEmail(
    subject="Price Protection - Model Y",
    body="""
Dear Daan,

This email is to inform you about upcoming price protection for our Model Y (MPC: MY-456).

Effective immediately, we are offering price protection for all existing stock of Model Y purchased within the last 30 days, against the new lower purchase price starting next week.

Please submit your claims for eligible stock by the end of the month.

Regards,

[Vendor Contact]
""",
    sender="vendorB@example.com",
    to=["daan.veld@coolblue.nl"]
)

thread2_email2 = MockEmail(
    subject="Fwd: Price Protection - Model Y",
    body="""
FYI - received this from Vendor B regarding Model Y price protection. As per our definition, this isn't a rebate request for the agent to process. It's a standard price protection notice.

Daan
""",
    sender="daan.veld@coolblue.nl",
    to=["j.lucvanderheijden@coolblue.nl"]
)

# --- Thread 3: Rebate with Missing Information ---
thread3_email1 = MockEmail(
    subject="Special Discount on Gadget Z",
    body="""
Hi Team,

We're excited to offer a special discount on our new Gadget Z (MPC: GZ-101)!

This is a limited-time offer. Get a great deal on this popular item.

Let us know if you're interested!

Thanks,

[Vendor Contact]
""",
    sender="vendorC@example.com",
    to=["daan.veld@coolblue.nl"]
)

thread3_email2 = MockEmail(
    subject="RE: Special Discount on Gadget Z - Rebate Details Needed",
    body="""
Hi [Vendor Contact],

Thanks for reaching out about Gadget Z.

To properly evaluate this offer, could you please provide the following details?
1.  Is this a rebate (sell-in or sell-out)?
2.  What is the specific rebate amount or factor per unit?
3.  What are the exact start and end dates for this offer?
4.  Which subsidiaries (NL, BE, DE) does this apply to?
5.  Is there a maximum quantity eligible for the discount?

Without these details, we cannot process this as a rebate request.

Thanks for your clarification!

Daan Veld
""",
    sender="vendorC@example.com",
    to=["daan.veld@coolblue.nl"]
)


# --- Group emails into MockGmailThread objects ---

# Thread 1
thread1_messages = [thread1_email1, thread1_email2, thread1_email3]
mock_thread1 = MockGmailThread(thread_id="thread_abc123", messages=thread1_messages)

# Thread 2
thread2_messages = [thread2_email1, thread2_email2]
mock_thread2 = MockGmailThread(thread_id="thread_def456", messages=thread2_messages)

# Thread 3
thread3_messages = [thread3_email1, thread3_email2]
mock_thread3 = MockGmailThread(thread_id="thread_ghi789", messages=thread3_messages)

# --- Simulate the output of ezgmail.search() ---
# This list contains MockGmailThread objects, just like ezgmail.search() would return
mock_ezgmail_search_output = [mock_thread1, mock_thread2, mock_thread3]


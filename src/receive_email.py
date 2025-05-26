import asyncio
import imaplib
import email
import pandas as pd
from email.header import decode_header


def load_email_accounts_from_csv(filepath):
    df = pd.read_csv(filepath)
    accounts = df.to_dict(orient='records')
    return accounts

queue = asyncio.Queue()

def clean_subject(subject):
    decoded, encoding = decode_header(subject)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding if encoding else 'utf-8')
    return decoded

def fetch_unseen_emails(account):
    mail = imaplib.IMAP4_SSL(account["imap_server"])
    mail.login(account["email"], account["password"])
    mail.select("inbox")

    status, messages = mail.search(None, f'(UNSEEN FROM "{account["from_filter"]}")')
    if status != "OK":
        print(f"❌ Failed for {account['email']}")
        mail.logout()
        return []

    email_ids = messages[0].split()
    unseen_emails = []
    for num in email_ids:
        status, data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(data[0][1])
        unseen_emails.append(msg)
    mail.logout()
    return unseen_emails

async def simulate_heavy_task(subject, sender):
    print(f"⚙️ Starting heavy task for: {subject} from {sender}")
    await asyncio.sleep(5) 
    print(f"✅ Finished heavy task for: {subject}")

async def listener_loop():
    while True:
        EMAIL_ACCOUNTS = load_email_accounts_from_csv("Emails.csv")
        for account in EMAIL_ACCOUNTS:
            unseen_emails = await asyncio.to_thread(fetch_unseen_emails, account)
            for msg in unseen_emails:
                await queue.put((account["email"], msg))
        await asyncio.sleep(30)

async def worker_loop(worker_name):
    while True:
        email_address, msg = await queue.get()
        subject = clean_subject(msg["Subject"])
        print(f"\n📩 [{worker_name}] New email for {email_address}")
        print(f"Subject: {subject}")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        print(f"Body: {body}")

        asyncio.create_task(simulate_heavy_task(subject, email_address))

        queue.task_done()


async def main():
    workers = [asyncio.create_task(worker_loop(f"Worker-{i}")) for i in range(3)]
    listener = asyncio.create_task(listener_loop())
    await asyncio.gather(listener, *workers)

if __name__ == "__main__":
    asyncio.run(main())

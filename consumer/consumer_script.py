import redis


r = redis.Redis(host="redis", port=6379, decode_responses=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def consume_events():
    last_id = "0"  # Start from the beginning
    while True:
        # Blocking read from Redis Stream
        events = r.xread({"messages": last_id}, block=0, count=1)
        if events:
            stream, messages = events[0]
            for message_id, message_data in messages:
                try:
                    db = get_db()
                    new_message = MessageModel(session_id=message_data.session_id, text=message_data.text, is_from_user=message_data.is_from_user)
                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)
                    
                    last_id = message_id  # Update last_id to avoid reprocessing
                except Exception as e:
                    print(f"got error while saving into database: {e}")

if __name__ == "__main__":
    consume_events()
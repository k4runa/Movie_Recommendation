
import asyncio
import os
from sqlalchemy import select, delete, and_, or_, func
import services.database
from services.database import Conversation, Message

async def cleanup_database():
    print("Starting database cleanup...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found!")
        return

    services.database.init_database(db_url)
    
    async with services.database._session_maker() as session:
        # 1. Find all conversations and fix order (user1_id < user2_id)
        stmt = select(Conversation)
        res = await session.execute(stmt)
        convs = res.scalars().all()
        
        print(f"Checking {len(convs)} conversations...")
        
        seen_pairs = {} # (u1, u2) -> conv_id
        
        for c in convs:
            u1, u2 = sorted([c.user1_id, c.user2_id])
            pair = (u1, u2)
            
            if pair in seen_pairs:
                # DUPLICATE FOUND!
                existing_id = seen_pairs[pair]
                print(f"Found duplicate: {pair}. Merging {c.id} into {existing_id}")
                
                # Update messages of the duplicate to point to the canonical one if we had a conversation_id field
                # But our messages link via sender/receiver, not conv_id. 
                # So we just need to ensure the status of the "best" one is preserved.
                
                existing_stmt = select(Conversation).where(Conversation.id == existing_id)
                existing_res = await session.execute(existing_stmt)
                existing_conv = existing_res.scalar_one()
                
                if c.status == "ACCEPTED":
                    existing_conv.status = "ACCEPTED"
                
                # Delete the duplicate
                await session.delete(c)
            else:
                # First time seeing this pair. Ensure u1 < u2
                if c.user1_id != u1 or c.user2_id != u2:
                    print(f"Fixing order for {c.id}: {c.user1_id},{c.user2_id} -> {u1},{u2}")
                    c.user1_id = u1
                    c.user2_id = u2
                seen_pairs[pair] = c.id
        
        await session.commit()
        print("Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup_database())

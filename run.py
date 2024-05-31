import asyncio
import os

from dotenv import load_dotenv

from app.mibot import MiBot

load_dotenv()
if __name__ == "__main__":
    asyncio.run(
        MiBot(
            mi_account_info={
                "mi_user": os.environ["MI_USER"],
                "mi_pass": os.environ["MI_PASS"],
                "mi_did": os.environ["MI_DID"],
            },
            hardware=os.environ["DEVICE_TYPE"],
            llm_options={
                "api_key": os.environ["API_KEY"],
                "model": os.environ["MODEL"],
                "base_url": os.environ["BASE_URL"]
            },
            use_command=True
        )
        .run_forever()
    )

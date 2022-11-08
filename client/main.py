import asyncio

from solana import system_program
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from solana.keypair import Keypair
from anchorpy.program.context import Context
from solana.rpc.commitment import Finalized
from solana.sysvar import SYSVAR_RENT_PUBKEY

from spl.token.instructions import get_associated_token_address
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID

from anchorpy import Program, Provider, Wallet

# import program_id


LAMPORTS_PER_SOL = 1000000000

async def generate_keypair(connection : AsyncClient):
    keypair = Keypair()

    resp = await connection.request_airdrop(keypair.public_key, int(0.3 * LAMPORTS_PER_SOL))
    await connection.confirm_transaction(resp.value, commitment=Finalized)
    return keypair


async def derive_pda(color : str, pubkey : PublicKey, program : Program):
    (pda, _) = PublicKey.find_program_address([
        pubkey.__bytes__(),
        "_".encode(encoding= 'UTF-8'),
        color.encode(encoding= 'UTF-8')
        ], program.program_id)
    return pda
    

async def create_ledger_account(color : str, pda : PublicKey, wallet : Keypair, program : Program, connection : AsyncClient):

    print("Creating account")
    create_ledger = program.rpc["create_ledger"]
    print(create_ledger)

    ctx = Context(accounts= {
        "ledger_account" : pda,
        "wallet" : wallet.public_key,
        "system_program": system_program.SYS_PROGRAM_ID,
        }, signers= [wallet])

    resp = await create_ledger(color, ctx=ctx)
    await connection.confirm_transaction(resp, commitment= Finalized)

    print(f"account created: {pda}")

async def modify_ledger_account(color : str, new_balance : int, wallet : Keypair, program : Program, connection : AsyncClient):


    pda = await derive_pda(color, wallet.public_key ,program)

    print(f"Checkong if account {pda} exists for color: {color}")
    try:
        data = await program.account["Ledger"].fetch(pda)
        print("It does.")
        print(f"data is {data}")
    except Exception as e:
        # raise e
        # print(e)
        print("It doesn't. Creating it...")
        await create_ledger_account(color, pda, wallet, program, connection)
        data = await program.account["Ledger"].fetch(pda)
        print(f"data is {data}")


    print("Sucess.")
    print("Current Data:")
    print(f"          Color: {data.color} Balance {data.balance}")
    print(f"Modifying balance of {data.color} from {data.balance} to {new_balance}")

    modify_ledger = program.rpc["modify_ledger"]
    ctx = Context(accounts= {
        "ledger_account" : pda,
        "wallet" : wallet.public_key,
        }, signers= [wallet])

    resp = await modify_ledger(new_balance, ctx = ctx)
    await connection.confirm_transaction(resp, commitment= Finalized)
    data = await program.account["Ledger"].fetch(pda)
    print("Successfully modified")
    print("New Data:")
    print(f"          Color: {data.color} Balance {data.balance}")





async def main():
    program_id = PublicKey("CUHtiUABtEJKnCjut9Z7KK2j8nF7WN7QJjhbSrr9DHZB")

    client = AsyncClient("http://localhost:8899")
    # client = AsyncClient("https://api.devnet.solana.com")
    provider = Provider(client, Wallet.local())
    # load the Program .
    program = await Program.at(
        program_id, provider
    )

    print(f"Program name is {program.idl.name}")

    wallet = Wallet.local()
    print(f"using wallet : {wallet.public_key}")

    # data = await program.account["Ledger"].fetch(PublicKey("2a5TgvSPuhFV1QLEYmVhfZuYG56ukYJUoaS3pH4qesBt"))
    # print(data)

    test_keypair = await generate_keypair(client)

    await modify_ledger_account("red", 2, test_keypair, program, client)

    await modify_ledger_account("red", 4, test_keypair, program, client)

    await modify_ledger_account("blue", 2, test_keypair, program, client)

    test_keypair2 = await generate_keypair(client)

    
    await modify_ledger_account("red", 3, test_keypair2, program, client)
    await modify_ledger_account("green", 3, test_keypair2, program, client)


    await program.close()

asyncio.run(main())

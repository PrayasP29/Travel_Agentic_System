"""Phase A verification: test all tool file async functions directly."""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_flight():
    from tools.flight_tools import search_flights
    print('=== flight_tools: search_flights ===')
    r = await search_flights(origin='LOND', destination='NYC', event_date='2026-07-15')
    print(f'  Status: {r.get("status")}')
    if r.get('status') == 'error':
        err = str(r.get('error', ''))
        if 'no running event loop' in err:
            print('  ERROR: asyncio error found!')
        elif 'ExceptionGroup' in err:
            print('  Expected: ExceptionGroup (tool name mismatch)')
        else:
            print(f'  Error: {err[:200]}')
    else:
        print(f'  Success! data keys: {list(r.get("data", {}).keys())}')

async def test_hotel():
    from tools.hotel_tools import search_hotels
    print('=== hotel_tools: search_hotels ===')
    r = await search_hotels(destination='New York')
    print(f'  Status: {r.get("status")}')
    if r.get('status') == 'error':
        err = str(r.get('error', ''))
        if 'no running event loop' in err:
            print('  ERROR: asyncio error found!')
        else:
            print(f'  Error: {err[:200]}')
    else:
        print('  Success!')

async def test_weather():
    from tools.weather_tools import get_weather
    print('=== weather_tools: get_weather ===')
    r = await get_weather(destination='New York', event_date='2026-07-15')
    print(f'  Status: {r.get("status")}')
    if r.get('status') == 'error':
        err = str(r.get('error', ''))
        if 'no running event loop' in err:
            print('  ERROR: asyncio error found!')
        else:
            print(f'  Error: {err[:200]}')
    else:
        print(f'  Success! keys: {list(r.keys())}')

async def main():
    await test_flight()
    print()
    await test_hotel()
    print()
    await test_weather()
    print()
    print('Phase A Verification complete')

asyncio.run(main())

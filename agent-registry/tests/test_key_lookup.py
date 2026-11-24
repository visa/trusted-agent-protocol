"""Exercise key lookup and agent deactivation against an actual SQLite database."""
import os
from pathlib import Path
import sys
import unittest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base
from main import deactivate_agent, get_agent_key, get_key_by_id
from models import Agent, AgentKey


class KeyLookupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.agent = Agent(name='Test agent', domain='https://agent.example', is_active='true')
        self.db.add(self.agent)
        self.db.flush()
        self.key = AgentKey(agent_id=self.agent.id, key_id='test-key',
                            public_key='synthetic-public-key', algorithm='ed25519', is_active='true')
        self.db.add(self.key)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_active_agent_and_key_are_returned(self):
        result = await get_key_by_id('test-key', self.db)
        self.assertEqual(result['key_id'], 'test-key')
        self.assertEqual(result['agent_id'], self.agent.id)
        self.assertEqual(result['is_active'], 'true')

    async def test_deactivated_agent_key_is_not_available_by_key_id(self):
        await deactivate_agent(self.agent.id, self.db)
        self.db.refresh(self.agent)
        self.assertEqual(self.agent.is_active, 'false')
        with self.assertRaises(HTTPException) as error:
            await get_key_by_id('test-key', self.db)
        self.assertEqual(error.exception.status_code, 404)

    async def test_agent_specific_lookup_also_rejects_deactivation(self):
        await deactivate_agent(self.agent.id, self.db)
        with self.assertRaises(HTTPException) as error:
            await get_agent_key(self.agent.id, 'test-key', self.db)
        self.assertEqual(error.exception.status_code, 404)

    async def test_key_deactivation_is_preserved_when_agent_is_reactivated(self):
        self.key.is_active = 'false'
        self.db.commit()
        await deactivate_agent(self.agent.id, self.db)
        self.agent.is_active = 'true'
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            await get_key_by_id('test-key', self.db)
        self.assertEqual(error.exception.status_code, 404)

    async def test_missing_key_is_not_found(self):
        with self.assertRaises(HTTPException) as error:
            await get_key_by_id('missing', self.db)
        self.assertEqual(error.exception.status_code, 404)

if __name__ == '__main__':
    unittest.main()

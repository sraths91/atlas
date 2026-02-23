"""
Integration Tests for Agent-Server Communication

Phase 8: Testing Infrastructure

Tests the interaction between FleetAgent and FleetServer components.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch
from copy import deepcopy


@pytest.mark.integration
class TestAgentServerCommunication:
    """Integration tests for agent-server communication"""

    def test_agent_report_flow(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test complete agent report flow"""
        # Simulate agent sending report
        machine_id = 'test-agent-1'

        # Server receives and processes report
        improved_data_store.update_machine(machine_id, sample_machine_info, sample_metrics)

        # Verify machine registered
        machine = improved_data_store.get_machine(machine_id)
        assert machine is not None
        assert machine['status'] == 'online'
        assert machine['info']['hostname'] == 'test-machine'

        # Verify metrics stored
        history = improved_data_store.get_machine_history(machine_id)
        assert len(history) == 1
        assert history[0]['metrics']['cpu']['percent'] == 45.2

    def test_command_queue_flow(self, improved_data_store):
        """Test command queuing and retrieval"""
        machine_id = 'test-agent-1'

        # Server queues command for agent
        command = {
            'id': 'cmd-123',
            'type': 'restart',
            'params': {},
            'created_at': '2025-12-31T12:00:00'
        }
        improved_data_store.add_command(machine_id, command)

        # Agent polls for commands
        pending_commands = improved_data_store.get_pending_commands(machine_id)
        assert len(pending_commands) == 1
        assert pending_commands[0]['id'] == 'cmd-123'

        # Agent acknowledges command
        result = improved_data_store.remove_command(machine_id, 'cmd-123')
        assert result is True

        # Verify command removed
        pending_commands = improved_data_store.get_pending_commands(machine_id)
        assert len(pending_commands) == 0

    def test_health_check_flow(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test health check flow"""
        machine_id = 'test-agent-1'

        # Agent registers
        improved_data_store.update_machine(machine_id, sample_machine_info, sample_metrics)

        # Server performs health check
        health_data = {
            'agent_version': '1.0.0',
            'uptime_seconds': 3600,
            'responsive': True
        }
        improved_data_store.update_health_check(
            machine_id,
            status='reachable',
            health_data=health_data,
            latency_ms=25
        )

        # Verify health status
        machine = improved_data_store.get_machine(machine_id)
        assert machine['health_check']['status'] == 'reachable'
        assert machine['health_check']['latency_ms'] == 25
        assert machine['health_check']['agent_responsive'] is True

    @pytest.mark.slow
    def test_concurrent_agent_reports(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test multiple agents reporting concurrently"""
        num_agents = 10
        reports_per_agent = 5
        errors = []

        def agent_reporter(agent_id):
            try:
                for i in range(reports_per_agent):
                    metrics = sample_metrics.copy()
                    metrics['cpu']['percent'] = 40 + (agent_id * 5) + i
                    improved_data_store.update_machine(
                        f'agent-{agent_id}',
                        sample_machine_info,
                        metrics
                    )
                    time.sleep(0.01)
            except Exception as e:
                errors.append((agent_id, str(e)))

        # Start all agents concurrently
        threads = [threading.Thread(target=agent_reporter, args=(i,)) for i in range(num_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all agents registered
        machines = improved_data_store.get_all_machines()
        assert len(machines) == num_agents

        # Verify each agent has correct history
        for i in range(num_agents):
            history = improved_data_store.get_machine_history(f'agent-{i}')
            assert len(history) == reports_per_agent

    def test_fleet_summary_with_multiple_agents(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test fleet summary with multiple reporting agents"""
        # Add agents with varying metrics
        agents = [
            ('agent-1', 30.0, 40.0, 50.0),  # Low resources
            ('agent-2', 95.0, 95.0, 95.0),  # High resources (should alert)
            ('agent-3', 60.0, 70.0, 80.0),  # Medium resources
        ]

        for agent_id, cpu, memory, disk in agents:
            metrics = deepcopy(sample_metrics)
            metrics['cpu']['percent'] = cpu
            metrics['memory']['percent'] = memory
            metrics['disk']['percent'] = disk
            improved_data_store.update_machine(agent_id, sample_machine_info, metrics)

        # Get fleet summary
        summary = improved_data_store.get_fleet_summary()

        assert summary['total_machines'] == 3
        assert summary['online'] == 3
        assert summary['avg_cpu'] == pytest.approx(61.67, 0.1)  # (30 + 95 + 60) / 3

        # Verify alerts
        alerts = summary['alerts']
        assert len(alerts) == 3  # CPU, Memory, Disk for agent-2
        assert all(a['machine_id'] == 'agent-2' for a in alerts)

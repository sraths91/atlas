"""
Unit Tests for FleetDataStore and ImprovedFleetDataStore

Phase 8: Testing Infrastructure
"""
import pytest
import time
import threading
from datetime import datetime
from copy import deepcopy


@pytest.mark.unit
class TestFleetDataStore:
    """Tests for original FleetDataStore"""

    def test_init(self, fleet_data_store):
        """Test data store initialization"""
        assert fleet_data_store.history_size == 100
        assert len(fleet_data_store.machines) == 0
        assert len(fleet_data_store.metrics_history) == 0

    def test_update_machine(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test updating machine data"""
        fleet_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        machine = fleet_data_store.get_machine('machine-1')
        assert machine is not None
        assert machine['machine_id'] == 'machine-1'
        assert machine['status'] == 'online'
        assert machine['info']['hostname'] == 'test-machine'
        assert machine['latest_metrics']['cpu']['percent'] == 45.2

    def test_get_machine_not_found(self, fleet_data_store):
        """Test getting non-existent machine"""
        machine = fleet_data_store.get_machine('nonexistent')
        assert machine is None

    def test_get_all_machines(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test getting all machines"""
        # Add multiple machines
        for i in range(3):
            fleet_data_store.update_machine(f'machine-{i}', sample_machine_info, sample_metrics)

        machines = fleet_data_store.get_all_machines()
        assert len(machines) == 3
        assert all(m['status'] == 'online' for m in machines)

    def test_machine_status_transitions(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test machine status transitions based on last_seen"""
        fleet_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        # Manually set last_seen to simulate offline machine
        machine = fleet_data_store.machines['machine-1']
        old_time = datetime.now().replace(year=2020).isoformat()
        machine['last_seen'] = old_time

        machines = fleet_data_store.get_all_machines()
        assert machines[0]['status'] == 'offline'

    def test_metrics_history(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test metrics history tracking"""
        # Add multiple metric entries
        for i in range(5):
            metrics = deepcopy(sample_metrics)
            metrics['cpu']['percent'] = 40 + i
            fleet_data_store.update_machine('machine-1', sample_machine_info, metrics)

        history = fleet_data_store.get_machine_history('machine-1')
        assert len(history) == 5
        assert history[0]['metrics']['cpu']['percent'] == 40
        assert history[4]['metrics']['cpu']['percent'] == 44

    def test_history_limit(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test history size limit"""
        # Add more entries than limit
        for i in range(150):
            fleet_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        history = fleet_data_store.get_machine_history('machine-1')
        assert len(history) <= 100  # Should be limited to history_size

    def test_fleet_summary(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test fleet-wide summary statistics"""
        # Add machines with different metrics
        for i in range(3):
            metrics = deepcopy(sample_metrics)
            metrics['cpu']['percent'] = 50 + (i * 10)
            fleet_data_store.update_machine(f'machine-{i}', sample_machine_info, metrics)

        summary = fleet_data_store.get_fleet_summary()
        assert summary['total_machines'] == 3
        assert summary['online'] == 3
        assert summary['avg_cpu'] == 60.0  # (50 + 60 + 70) / 3

    def test_critical_alerts(self, fleet_data_store, sample_machine_info, sample_metrics):
        """Test critical resource alerts"""
        # Add machine with high CPU
        high_metrics = deepcopy(sample_metrics)
        high_metrics['cpu']['percent'] = 95.0
        fleet_data_store.update_machine('machine-1', sample_machine_info, high_metrics)

        summary = fleet_data_store.get_fleet_summary()
        assert len(summary['alerts']) == 1
        assert summary['alerts'][0]['type'] == 'cpu'
        assert summary['alerts'][0]['severity'] == 'critical'


@pytest.mark.unit
class TestImprovedFleetDataStore:
    """Tests for ImprovedFleetDataStore"""

    def test_init(self, improved_data_store):
        """Test improved data store initialization"""
        assert improved_data_store.history_size == 100
        assert len(improved_data_store.machines) == 0
        assert len(improved_data_store.metrics_history) == 0

    def test_concurrent_reads(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test concurrent read operations don't block each other"""
        # Add test data
        improved_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        results = []
        errors = []

        def reader(thread_id):
            try:
                start = time.time()
                machine = improved_data_store.get_machine('machine-1')
                elapsed = time.time() - start
                results.append((thread_id, elapsed, machine is not None))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start 5 concurrent readers
        threads = [threading.Thread(target=reader, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        assert all(success for _, _, success in results)

    def test_deep_copy_protection(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test that returned data is deep copied and mutations don't affect store"""
        improved_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        # Get machine and mutate it
        machine1 = improved_data_store.get_machine('machine-1')
        machine1['info']['hostname'] = 'mutated'
        machine1['latest_metrics']['cpu']['percent'] = 999

        # Get machine again - should be unchanged
        machine2 = improved_data_store.get_machine('machine-1')
        assert machine2['info']['hostname'] == 'test-machine'
        assert machine2['latest_metrics']['cpu']['percent'] == 45.2

    def test_command_queue(self, improved_data_store):
        """Test command queue operations"""
        # Add commands
        cmd1 = {'id': 'cmd-1', 'type': 'restart', 'created_at': datetime.now().isoformat()}
        cmd2 = {'id': 'cmd-2', 'type': 'update', 'created_at': datetime.now().isoformat()}

        improved_data_store.add_command('machine-1', cmd1)
        improved_data_store.add_command('machine-1', cmd2)

        # Get pending commands
        commands = improved_data_store.get_pending_commands('machine-1')
        assert len(commands) == 2
        assert commands[0]['id'] == 'cmd-1'
        assert commands[1]['id'] == 'cmd-2'

    def test_remove_command(self, improved_data_store):
        """Test removing command from queue"""
        cmd = {'id': 'cmd-1', 'type': 'restart', 'created_at': datetime.now().isoformat()}
        improved_data_store.add_command('machine-1', cmd)

        # Remove command
        result = improved_data_store.remove_command('machine-1', 'cmd-1')
        assert result is True

        # Verify removed
        commands = improved_data_store.get_pending_commands('machine-1')
        assert len(commands) == 0

        # Try removing again
        result = improved_data_store.remove_command('machine-1', 'cmd-1')
        assert result is False

    def test_health_check_update(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test health check status updates"""
        improved_data_store.update_machine('machine-1', sample_machine_info, sample_metrics)

        health_data = {
            'agent_version': '1.0.0',
            'uptime_seconds': 3600,
            'responsive': True
        }

        improved_data_store.update_health_check(
            'machine-1',
            status='reachable',
            health_data=health_data,
            latency_ms=50
        )

        machine = improved_data_store.get_machine('machine-1')
        assert 'health_check' in machine
        assert machine['health_check']['status'] == 'reachable'
        assert machine['health_check']['latency_ms'] == 50
        assert machine['health_check']['agent_version'] == '1.0.0'

    @pytest.mark.slow
    def test_concurrent_write_safety(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test that concurrent writes maintain data consistency"""
        errors = []

        def writer(machine_id, count):
            try:
                for i in range(count):
                    metrics = sample_metrics.copy()
                    metrics['cpu']['percent'] = 50 + i
                    improved_data_store.update_machine(
                        f'machine-{machine_id}',
                        sample_machine_info,
                        metrics
                    )
                    time.sleep(0.001)
            except Exception as e:
                errors.append((machine_id, str(e)))

        # Start 5 concurrent writers
        threads = [threading.Thread(target=writer, args=(i, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all machines were created
        machines = improved_data_store.get_all_machines()
        assert len(machines) == 5

        # Verify each machine has correct history
        for i in range(5):
            history = improved_data_store.get_machine_history(f'machine-{i}')
            assert len(history) == 10

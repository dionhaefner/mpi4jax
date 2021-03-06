#!/usr/bin/env python

"""
Run with

$ mpirun -n <nproc> python -m pytest .
"""

import pytest

import jax
import jax.config
import jax.numpy as jnp

jax.config.enable_omnistaging()

from mpi4py import MPI  # noqa: E402

print(MPI.get_vendor())

rank = MPI.COMM_WORLD.Get_rank()
size = MPI.COMM_WORLD.Get_size()

print("MPI rank = ", rank)
print("MPI size = ", size)


def test_allreduce():
    from mpi4jax import Allreduce

    arr = jnp.ones((3, 2))
    _arr = arr.copy()

    res, token = Allreduce(arr, op=MPI.SUM)
    assert jnp.array_equal(res, arr * size)
    assert jnp.array_equal(_arr, arr)


def test_allreduce_jit():
    from mpi4jax import Allreduce

    arr = jnp.ones((3, 2))
    _arr = arr.copy()

    res, token = jax.jit(lambda x: Allreduce(x, op=MPI.SUM))(arr)
    assert jnp.array_equal(res, arr * size)
    assert jnp.array_equal(_arr, arr)


def test_allreduce_scalar():
    from mpi4jax import Allreduce

    arr = 1
    _arr = 1

    res, token = Allreduce(arr, op=MPI.SUM)
    assert jnp.array_equal(res, arr * size)
    assert jnp.array_equal(_arr, arr)


def test_allreduce_scalar_jit():
    from mpi4jax import Allreduce

    arr = 1
    _arr = 1

    res, token = jax.jit(lambda x: Allreduce(x, op=MPI.SUM))(arr)
    assert jnp.array_equal(res, arr * size)
    assert jnp.array_equal(_arr, arr)


def test_send_recv():
    from mpi4jax import Send, Recv

    arr = jnp.ones((3, 2)) * rank
    _arr = arr.copy()

    if rank == 0:
        for proc in range(1, size):
            res, token = Recv(arr, source=proc, tag=proc)
            assert jnp.array_equal(res, jnp.ones_like(arr) * proc)
            assert jnp.array_equal(_arr, arr)
    else:
        Send(arr, 0, tag=rank)
        assert jnp.array_equal(_arr, arr)


def test_send_recv_scalar():
    from mpi4jax import Send, Recv

    arr = 1 * rank
    _arr = 1 * rank

    if rank == 0:
        for proc in range(1, size):
            res, token = Recv(arr, source=proc, tag=proc)
            assert jnp.array_equal(res, jnp.ones_like(arr) * proc)
            assert jnp.array_equal(_arr, arr)
    else:
        Send(arr, 0, tag=rank)
        assert jnp.array_equal(_arr, arr)


def test_send_recv_scalar_jit():
    from mpi4jax import Send, Recv

    arr = 1 * rank
    _arr = 1 * rank

    if rank == 0:
        for proc in range(1, size):
            res, token = jax.jit(lambda x: Recv(x, source=proc, tag=proc))(arr)
            assert jnp.array_equal(res, jnp.ones_like(arr) * proc)
            assert jnp.array_equal(_arr, arr)
    else:
        jax.jit(lambda x: Send(x, 0, tag=rank))(arr)
        assert jnp.array_equal(_arr, arr)


def test_send_recv_jit():
    from mpi4jax import Send, Recv

    arr = jnp.ones((3, 2)) * rank
    _arr = arr.copy()

    if rank == 0:
        for proc in range(1, size):
            res, token = jax.jit(lambda x: Recv(x, source=proc, tag=proc))(arr)
            assert jnp.array_equal(res, jnp.ones_like(arr) * proc)
            assert jnp.array_equal(_arr, arr)
    else:
        jax.jit(lambda x: Send(x, 0, tag=rank))(arr)
        assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(size < 2 or rank > 1, reason="Runs only on rank 0 and 1")
def test_send_recv_deadlock():
    from mpi4jax import Send, Recv

    # this deadlocks without proper token management
    @jax.jit
    def deadlock(arr):
        if rank == 0:
            # send, then receive
            token = Send(arr, 1)
            newarr, _ = Recv(arr, 1, token=token)
        else:
            # receive, then send
            newarr, token = Recv(arr, 0)
            Send(arr, 0, token=token)
        return newarr

    arr = jnp.ones(10) * rank
    arr = deadlock(arr)
    assert jnp.array_equal(arr, jnp.ones_like(arr) * (1 - rank))


def test_send_recv_status():
    from mpi4jax import Send, Recv

    arr = jnp.ones((3, 2)) * rank
    _arr = arr.copy()

    if rank == 0:
        for proc in range(1, size):
            status = MPI.Status()
            res, token = jax.jit(
                lambda x: Recv(x, source=proc, tag=proc, status=status)
            )(arr)
            assert jnp.array_equal(res, jnp.ones_like(arr) * proc)
            assert jnp.array_equal(_arr, arr)
            assert status.Get_source() == proc
    else:
        jax.jit(lambda x: Send(x, 0, tag=rank))(arr)
        assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(size < 2 or rank > 1, reason="Runs only on rank 0 and 1")
def test_sendrecv():
    from mpi4jax import Sendrecv

    arr = jnp.ones((3, 2)) * rank
    _arr = arr.copy()

    other = 1 - rank

    res, token = Sendrecv(arr, arr, source=other, dest=other)

    assert jnp.array_equal(res, jnp.ones_like(arr) * other)
    assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(size < 2 or rank > 1, reason="Runs only on rank 0 and 1")
def test_sendrecv_scalar():
    from mpi4jax import Sendrecv

    arr = 1 * rank
    _arr = arr

    other = 1 - rank

    res, token = Sendrecv(arr, arr, source=other, dest=other)

    assert jnp.array_equal(res, jnp.ones_like(arr) * other)
    assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(size < 2 or rank > 1, reason="Runs only on rank 0 and 1")
def test_sendrecv_jit():
    from mpi4jax import Sendrecv

    arr = jnp.ones((3, 2)) * rank
    _arr = arr.copy()

    other = 1 - rank

    res, token = jax.jit(lambda x, y: Sendrecv(x, y, source=other, dest=other))(
        arr, arr
    )

    assert jnp.array_equal(res, jnp.ones_like(arr) * other)
    assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(size < 2 or rank > 1, reason="Runs only on rank 0 and 1")
def test_sendrecv_scalar_jit():
    from mpi4jax import Sendrecv

    arr = 1 * rank
    _arr = arr

    other = 1 - rank

    res, token = jax.jit(lambda x, y: Sendrecv(x, y, source=other, dest=other))(
        arr, arr
    )

    assert jnp.array_equal(res, jnp.ones_like(arr) * other)
    assert jnp.array_equal(_arr, arr)


@pytest.mark.skipif(rank > 0, reason="Runs only on rank 0")
def test_abort_on_error(tmp_path):
    # hacky but I think this is the only way not to kill the testing process itself
    import os
    import sys
    import subprocess
    from textwrap import dedent

    test_script = dedent("""
        import jax
        jax.config.enable_omnistaging()
        import jax.numpy as jnp

        from mpi4py import MPI
        from mpi4jax import Send

        comm = MPI.COMM_WORLD
        assert comm.Get_size() == 1

        # send to non-existing rank
        jax.jit(lambda x: Send(x, dest=100, comm=comm))(
            jnp.ones(10)
        )

        # sleep so the process doesn't exit before running the function
        import time
        time.sleep(1)
    """)

    test_file = tmp_path / "abort.py"
    test_file.write_text(test_script)

    proc = subprocess.run(
        [sys.executable, test_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=0, timeout=10, universal_newlines=True,
        # passing a mostly empty env seems to be the only way to
        # force MPI to initialize again
        env=dict(PATH=os.environ["PATH"]),
    )

    assert proc.returncode != 0
    assert "r0 | MPI_Send returned error code" in proc.stderr


def test_debug_logging_disabled(capsys, monkeypatch):
    from mpi4jax import Allreduce
    from mpi4jax.cython.mpi_xla_bridge import set_logging

    arr = jnp.ones((3, 2))

    set_logging(True)
    set_logging(False)

    res = jax.jit(lambda x: Allreduce(x, op=MPI.SUM))(arr)
    res[0].block_until_ready()

    captured = capsys.readouterr()
    assert not captured.out


def test_debug_logging_enabled(capsys, monkeypatch):
    from mpi4jax import Allreduce
    from mpi4jax.cython.mpi_xla_bridge import set_logging

    arr = jnp.ones((3, 2))
    try:
        set_logging(True)
        res = jax.jit(lambda x: Allreduce(x, op=MPI.SUM))(arr)
        res[0].block_until_ready()
    finally:
        set_logging(False)

    captured = capsys.readouterr()
    assert captured.out.startswith(f"r{rank} | MPI_Allreduce with token")

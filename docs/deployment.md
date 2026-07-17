# Three-host deployment

For a machine with no prior checkout, follow
[reproduction.md](reproduction.md). The canonical deployment input is one
unchanged manifest plus one immutable Git commit.

## Contract

- All three hosts receive byte-identical manifest files.
- Each checkout path equals that role's `repo_dir`.
- Git origin matches `[release].repository`; HEAD matches `[release].commit`.
- Host paths, network, devices, containers and runtime policy come only from
  the manifest. Fast DDS XML is generated from it during install/start.
- Credentials, models and caches remain external assets.

## Canonical command

```bash
bash deploy/role.sh <ai_max|server_pc|tb3> \
  <install|start|stop|restart|status> --manifest PATH
```

Initialize the standard user-scoped manifest once with:

```bash
bash deploy/role.sh manifest-init
```

After the completed file has been copied unchanged to
`~/.config/tb3/host-manifest.toml` on every host, `--manifest PATH` may be
omitted. An explicit flag or `TB3_HOST_MANIFEST` still overrides the default.

Do not mix this with direct component launch commands during normal operation.
The dispatcher owns processes, containers, PID files, state markers and logs.

Start AI Max, then Server PC, then TB3. Run install preflight before install and
runtime preflight after each start:

```bash
bash deploy/preflight.sh <role> --phase install --manifest PATH
bash deploy/role.sh <role> install --manifest PATH
bash deploy/role.sh <role> start --manifest PATH
bash deploy/role.sh <role> status --manifest PATH
bash deploy/preflight.sh <role> --phase runtime --manifest PATH
```

Stop in reverse order. Real motion remains disabled while
`[tb3].behavior_dry_run=true`.

## Verification endpoints

The manifest defines all addresses and ports:

- AI Max VLM `/health` and VLM Dashboard `/`;
- Server dashboard `/status.json`;
- TB3 UI `/state.json`;
- role-local `status` JSON and TB3 full-health script.

See [lifecycle.md](lifecycle.md) for ownership and status semantics, and
[troubleshooting.md](troubleshooting.md) for failures.

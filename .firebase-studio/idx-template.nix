{ pkgs, ... }: {
  # Add rsync to the bootstrap environment.
  packages = [
    pkgs.rsync
  ];

  # The bootstrap script runs in a temporary directory containing the
  # contents of your template folder.
  bootstrap = ''
    # Use rsync to copy the entire repository into the new workspace directory ($out).
    # rsync is more robust for this task. It excludes the .git and template
    # directories to avoid including unnecessary files in the workspace.
    rsync -a --exclude ".git" --exclude ".firebase-studio" ${./.}/../ "$out/"

    # Create the .idx directory for workspace configuration.
    mkdir -p "$out/.idx"

    # Create the dev.nix file that defines the workspace environment.
    cat > "$out/.idx/dev.nix" <<'EOF'
{pkgs}: {
  # Add required system packages.
  # pkgs.python312 provides python 3.12
  # pkgs.uv is a fast python package installer
  packages = [
    pkgs.python312
    pkgs.uv
  ];

  # Workspace lifecycle hooks allow running commands when the workspace
  # is created or started.
  idx.workspace.onCreate = {
    # Install python dependencies from pyproject.toml and uv.lock
    # using 'uv sync'. This runs when the workspace is first created.
    install-dependencies = "cd demo/ui && uv sync";
  };

  # Configure previews for the web application.
  idx.previews = {
    previews = [
      {
        id = "a2a-demo-ui";
        name = "A2A Demo UI";
        # Command to start the demo UI.
        # It changes into the 'demo/ui' directory and runs the main python script.
        command = "cd demo/ui && uv run main.py";
        # The port the application will be running on.
        port = 12000;
        # 'web' manager opens the preview in a browser tab inside Firebase Studio.
        manager = "web";
      }
    ];
  };
}
EOF

    # Set write permissions on the entire workspace.
    chmod -R +w "$out"
  '';
}

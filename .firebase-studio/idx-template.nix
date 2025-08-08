{ pkgs, ... }: {
  # The bootstrap script runs in a temporary directory containing the
  # contents of your template folder.
  bootstrap = ''
    # The full repository is checked out one level above the template directory.
    # Copy the entire repository into the new workspace directory ($out).
    # Enable dotglob to include hidden files in globbing
    shopt -s dotglob
    # Copy all files and directories from the repository root to the workspace
    for item in ${./.}/../*; do
      # Exclude .git and the template directory itself
      if [[ "$(basename "$item")" != ".git" && "$(basename "$item")" != ".firebase-studio" ]]; then
        cp -a "$item" "$out/"
      fi
    done

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

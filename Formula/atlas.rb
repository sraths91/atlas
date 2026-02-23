# Homebrew Formula for Atlas
class Atlas < Formula
  include Language::Python::Virtualenv

  desc "Enhanced system monitor for Turing Atlas on macOS"
  homepage "https://github.com/yourusername/atlas"
  url "https://github.com/yourusername/atlas/archive/v1.0.0.tar.gz"
  sha256 "YOUR_SHA256_HERE"  # Update this with actual SHA256
  license "MIT"

  depends_on "python@3.11"

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/source/p/psutil/psutil-5.9.6.tar.gz"
    sha256 "e4b92ddcd7dd4cdd3f900180ea1e104932c7bce234fb88976e2a3b296441225a"
  end

  resource "Pillow" do
    url "https://files.pythonhosted.org/packages/source/P/Pillow/Pillow-10.1.0.tar.gz"
    sha256 "e6bf8de6c36ed96c86ea3b6e1d5273c53f46ef518a062464cd7ef5dd2cf92e38"
  end

  resource "pyserial" do
    url "https://files.pythonhosted.org/packages/source/p/pyserial/pyserial-3.5.tar.gz"
    sha256 "3c77e014170dfffbd816e6ffc205e9842efb10be9f58ec16d3e8675b4925cddb"
  end

  resource "rumps" do
    url "https://files.pythonhosted.org/packages/source/r/rumps/rumps-0.4.0.tar.gz"
    sha256 "a8e1e3a3f0f5e5d4b6a9e6e8e6e8e6e8e6e8e6e8e6e8e6e8e6e8e6e8e6e8e6e8"
  end

  resource "Flask" do
    url "https://files.pythonhosted.org/packages/source/F/Flask/Flask-3.0.0.tar.gz"
    sha256 "cfadcdb638b609361d29ec22360d6070a77d7463dcb3ab08d2c2f2f168845f58"
  end

  def install
    virtualenv_install_with_resources
    
    # Create config directory
    (var/"atlas").mkpath
    
    # Install man page
    # man1.install "docs/atlas.1"
  end

  def post_install
    # Create default config
    config_dir = "#{ENV['HOME']}/.config/atlas"
    mkdir_p config_dir
    
    unless File.exist?("#{config_dir}/config.json")
      ohai "Creating default configuration..."
      system bin/"atlas", "--init-config"
    end
  end

  def caveats
    <<~EOS
      Atlas has been installed!
      
      To start the application:
        atlas
      
      To start in simulated mode (no hardware required):
        atlas --simulated
      
      To launch the theme editor:
        atlas-editor
      
      To start the menu bar app:
        atlas-menubar
      
      Configuration is stored in:
        ~/.config/atlas/
      
      For more information:
        atlas --help
    EOS
  end

  test do
    system bin/"atlas", "--version"
    system bin/"atlas", "--list-themes"
  end
end

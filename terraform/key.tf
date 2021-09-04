data "template_file" "pubkey" {
  template = file(pathexpand("~/.ssh/id_rsa.pub"))
}

resource "aws_key_pair" "main" {
  key_name   = "tomato"
  public_key = data.template_file.pubkey.rendered

  lifecycle {
    ignore_changes = [public_key]
  }
}

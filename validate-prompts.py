#!./python

import os
import argparse
import requests
from lxml import etree

# ANSI color codes for colored output
COLOR_OK = "\033[92m"       # Green
COLOR_ERROR = "\033[91m"    # Red
COLOR_WARNING = "\033[93m"  # Yellow
COLOR_RESET = "\033[0m"     # Reset color

def fetch_xsd(xsd_url: str) -> etree.XMLSchema:
    """Fetches an XSD file from a URL and returns an XMLSchema object.

    Args:
        xsd_url: URL of the XSD schema.

    Returns:
        XMLSchema object if successfully fetched, else None.
    """
    try:
        response = requests.get(xsd_url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP failures

        xsd_tree = etree.XML(response.content)
        return etree.XMLSchema(xsd_tree)
    except requests.RequestException as e:
        print(f"{COLOR_ERROR}[ERROR] Failed to fetch XSD from {xsd_url}: {e}{COLOR_RESET}")
        return None
    except etree.XMLSyntaxError as e:
        print(f"{COLOR_ERROR}[ERROR] Invalid XSD format from {xsd_url}: {e}{COLOR_RESET}")
        return None


def validate_xml(xml_path: str, xsd_override: str = None) -> bool:
    """Validates an XML file against its XSD.

    Args:
        xml_path: Path to the XML file.
        xsd_override: Optional local XSD file to use instead of the one in xsi:noNamespaceSchemaLocation.

    Returns:
        True if the XML is valid, False otherwise.
    """
    try:
        # Parse the XML file
        xml_tree = etree.parse(xml_path)
        root = xml_tree.getroot()

        # Use provided XSD if specified
        if xsd_override:
            xsd_path = xsd_override
        else:
            # Extract xsi:noNamespaceSchemaLocation (URL or file path)
            xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
            xsd_location = root.attrib.get(f"{{{xsi_ns}}}noNamespaceSchemaLocation")

            if not xsd_location:
                print(f"{COLOR_WARNING}[WARNING] No XSD location found in {xml_path}. Skipping validation.{COLOR_RESET}")
                return False

            # Determine if the XSD is a URL or local file
            if xsd_location.startswith(("http://", "https://")):
                xsd_schema = fetch_xsd(xsd_location)
                if not xsd_schema:
                    return False  # Failed to fetch or parse XSD
                return validate_with_schema(xml_tree, xsd_schema, xml_path)

            else:
                # Assume local file (relative to XML file location)
                xsd_path = os.path.join(os.path.dirname(xml_path), xsd_location)

        # Validate using the local XSD
        if not os.path.exists(xsd_path):
            print(f"{COLOR_ERROR}[ERROR] XSD file '{xsd_path}' not found.{COLOR_RESET}")
            return False

        xsd_tree = etree.parse(xsd_path)
        xsd_schema = etree.XMLSchema(xsd_tree)

        return validate_with_schema(xml_tree, xsd_schema, xml_path)

    except Exception as e:
        print(f"{COLOR_ERROR}[ERROR] Failed to validate {xml_path}: {e}{COLOR_RESET}")
        return False


def validate_with_schema(xml_tree: etree._ElementTree, xsd_schema: etree.XMLSchema, xml_path: str) -> bool:
    """Validates an XML tree against a provided XSD schema.

    Args:
        xml_tree: Parsed XML tree.
        xsd_schema: Compiled XSD schema.
        xml_path: Path to the XML file.

    Returns:
        True if the XML is valid, False otherwise.
    """
    if xsd_schema.validate(xml_tree):
        print(f"{COLOR_OK}[OK] {xml_path} is valid.{COLOR_RESET}")
        return True
    else:
        print(f"{COLOR_ERROR}[KO] {xml_path} is NOT valid.{COLOR_RESET}")
        print(xsd_schema.error_log)
        return False


def validate_xmls_in_directory(directory: str, xsd_override: str = None):
    """Validates all XML files in a given directory against their respective XSDs.

    Args:
        directory: Path to the directory containing XML files.
        xsd_override: Optional local XSD file to use instead of xsi:noNamespaceSchemaLocation.
    """
    if not os.path.isdir(directory):
        print(f"{COLOR_ERROR}[ERROR] '{directory}' is not a valid directory.{COLOR_RESET}")
        return

    xml_files = [f for f in os.listdir(directory) if f.endswith(".xml")]

    if not xml_files:
        return

    for xml_file in xml_files:
        xml_path = os.path.join(directory, xml_file)
        validate_xml(xml_path, xsd_override)


def main():
    """Parses command-line arguments and validates XML files."""
    parser = argparse.ArgumentParser(description="Validate XML files against XSD (local or online).")
    parser.add_argument("xml_path", help="Path to an XML file or directory containing XML files.")
    parser.add_argument("--xsd", help="Optional local XSD file to override xsi:noNamespaceSchemaLocation.", default=None)

    args = parser.parse_args()

    if os.path.isdir(args.xml_path):
        validate_xmls_in_directory(args.xml_path, args.xsd)
    else:
        validate_xml(args.xml_path, args.xsd)


if __name__ == "__main__":
    main()
